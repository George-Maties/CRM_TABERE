import random
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from apps.accounts.roles import FOUNDER, SELLER, sellers_and_founders
from apps.contacte.models import Contact
from apps.oportunitati.models import Note, Opportunity, Status
from apps.oportunitati.models import Task as OpportunityTask
from apps.tabere.models import Camp, Child

FIRST_NAMES = [
    "Ana",
    "Maria",
    "Elena",
    "Ioana",
    "Andreea",
    "Cristina",
    "Mihaela",
    "Alexandra",
    "Raluca",
    "Andrei",
    "Mihai",
    "Alexandru",
    "Ion",
    "George",
    "Radu",
    "Bogdan",
    "Florin",
    "Daniel",
]
LAST_NAMES = [
    "Popescu",
    "Ionescu",
    "Popa",
    "Pop",
    "Dumitrescu",
    "Stan",
    "Stoica",
    "Gheorghe",
    "Matei",
    "Constantin",
    "Marin",
    "Munteanu",
    "Lazăr",
    "Rusu",
    "Ciobanu",
    "Florea",
    "Toma",
    "Sârbu",
]
CITIES = ["Brașov", "Cluj", "București", "Sibiu", "Iași", "Timișoara", "Constanța", "Oradea"]
NOTES = [
    "Am sunat, revin mâine.",
    "Vrea oferta pe email pentru tabăra de vară.",
    "Întreabă de reducerea la frați.",
    "Nu a răspuns. Încerc din nou după-amiază.",
    "Confirmă săptămâna viitoare, după ce vorbește cu soțul.",
]


# Everything the command creates can be found again, and removed with --remove:
# contacts by their e-mail domain, camps by their notes.
EMAIL_DOMAIN = "@volum.example.ro"
CAMP_MARKER = "Date de test generate cu seed_load (se șterg cu: seed_load --remove)."
SEASONS = (("de iarnă", 2), ("de primăvară", 4), ("de vară", 7), ("de toamnă", 10))


class Command(BaseCommand):
    help = (
        "Fill the database with a realistic volume: contacts, opportunities, notes, tasks and "
        "camps with a set number of participants (and their children). Runs on a database "
        "whose name ends in _load, or on the current one with --here; --remove deletes it all."
    )

    def add_arguments(self, parser):
        parser.add_argument("--contacts", type=int, default=10_000)
        parser.add_argument("--camps", type=int, default=36)
        parser.add_argument(
            "--participants", type=int, default=25, help="Contacts (families) in each camp."
        )
        parser.add_argument("--seed", type=int, default=1, help="Same seed, same data.")
        parser.add_argument(
            "--here", action="store_true", help="Also on a database not named *_load."
        )
        parser.add_argument(
            "--remove", action="store_true", help="Delete what this command created, and stop."
        )

    @transaction.atomic
    def handle(self, *args, contacts, camps, participants, seed, here, remove, **options):
        name = settings.DATABASES["default"]["NAME"]
        if not (name.endswith("_load") or here or remove):
            raise CommandError(
                f"The database is {name!r}. Use a load-test database, e.g.:\n"
                "  createdb crm_tabere_load\n"
                "  DB_NAME=crm_tabere_load python manage.py migrate\n"
                "  DB_NAME=crm_tabere_load python manage.py setup_roles\n"
                "  DB_NAME=crm_tabere_load python manage.py seed_load\n"
                "or add --here to fill this one (seed_load --remove takes it out again)."
            )
        if remove:
            return self.remove()
        if camps * participants > contacts:
            raise CommandError(
                f"{camps} camps × {participants} participants need at least that many contacts."
            )
        people = list(sellers_and_founders())
        if not people:
            raise CommandError(f"Create a few users with the {FOUNDER!r} or {SELLER!r} role first.")
        rng = random.Random(seed)
        today = timezone.localdate()

        # Seasons around today, the most recent ones up to a year ahead: some camps are being
        # prepared, a few are running or close, most are over.
        new_camps = []
        for index in range(camps):
            season, month = SEASONS[index % len(SEASONS)]
            year = today.year + 1 - index // (len(SEASONS) * 3)
            series = index // len(SEASONS) % 3 + 1
            start = date(year, month, 1 + 7 * (series - 1))
            # One camp running now and one in its final details, so every status shows up
            if index in (0, 1):
                start = today + timedelta(days=(-2, 10)[index])
            new_camps.append(
                Camp(
                    name=f"Tabăra {season} {year}, seria {series}",
                    start_date=start,
                    end_date=start + timedelta(days=6),
                    notes=CAMP_MARKER,
                )
            )
        new_camps = Camp.objects.bulk_create(new_camps)

        new_contacts = Contact.objects.bulk_create(
            (
                Contact(
                    name=f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}",
                    kind=Contact.Kind.TEACHER if rng.random() < 0.1 else Contact.Kind.PARENT,
                    phone=f"07{rng.randrange(10**8):08d}",
                    email=f"contact{number}{EMAIL_DOMAIN}",
                )
                for number in range(contacts)
            ),
            batch_size=2000,
        )
        owners = {contact.pk: rng.choice(people) for contact in new_contacts}
        through = Contact.assignees.through
        through.objects.bulk_create(
            (
                through(contact_id=contact.pk, user_id=owners[contact.pk].pk)
                for contact in new_contacts
                if rng.random() < 0.85
            ),
            batch_size=5000,
        )

        numbers = {}  # contact id -> last opportunity number ("Ana Pop #2")

        def opportunity(contact, status, camp=None):
            numbers[contact.pk] = numbers.get(contact.pk, 0) + 1
            return Opportunity(
                contact=contact,
                number=numbers[contact.pk],
                status=status,
                camp=camp,
                owner=owners[contact.pk],
                # A teacher usually goes with the class; some parents come too.
                contact_goes=camp is not None
                and rng.random() < (0.8 if contact.kind == Contact.Kind.TEACHER else 0.1),
            )

        # Exactly `participants` families in each camp (a family may go to several camps)...
        new_opportunities = [
            opportunity(contact, Status.WON, camp)
            for camp in new_camps
            for contact in rng.sample(new_contacts, participants)
        ]
        # ...and the rest of the work: open and lost opportunities, 0 to 2 per contact.
        for contact in new_contacts:
            for _ in range(rng.choice((0, 0, 1, 1, 1, 2))):
                status = Status.POTENTIAL if rng.random() < 0.55 else Status.LOST
                new_opportunities.append(opportunity(contact, status))
        new_opportunities = Opportunity.objects.bulk_create(new_opportunities, batch_size=5000)

        notes, children, tasks = [], [], []
        for item in new_opportunities:
            for _ in range(rng.randint(1, 5)):
                notes.append(Note(opportunity=item, author=item.owner, text=rng.choice(NOTES)))
            if item.status == Status.LOST:
                notes.append(Note(opportunity=item, author=item.owner, text="A ales altă tabără."))
            if item.status != Status.POTENTIAL:
                change = f"Potențial → {Status(item.status).label}"
                if item.camp:
                    change += f" · {item.camp.name}"
                notes.append(
                    Note(
                        opportunity=item,
                        author=item.owner,
                        status_change=change,
                        new_status=item.status,
                    )
                )
            if item.status == Status.WON:
                for _ in range(rng.choice((1, 1, 1, 2, 2, 3))):
                    children.append(
                        Child(
                            opportunity=item,
                            name=f"{rng.choice(FIRST_NAMES)} {item.contact.name.split()[1]}",
                            age=rng.randint(6, 16),
                            city=rng.choice(CITIES),
                            medical_notes="Alergic la arahide." if rng.random() < 0.05 else "",
                        )
                    )
            if item.status == Status.POTENTIAL and rng.random() < 0.15:
                tasks.append(
                    OpportunityTask(
                        opportunity=item,
                        title="Sună pentru confirmare",
                        assigned_to=item.owner,
                        due_date=today + timedelta(days=rng.randint(-10, 30)),
                        done=rng.random() < 0.5,
                    )
                )
        Note.objects.bulk_create(notes, batch_size=10000)
        Child.objects.bulk_create(children, batch_size=5000)
        OpportunityTask.objects.bulk_create(tasks, batch_size=5000)

        # Spread the dates over the last years, as real data would be (auto_now ignores them
        # in bulk_create, so they are set here). Only on what was just created.
        mine = (
            "SELECT o.id FROM oportunitati_opportunity o JOIN contacte_contact c"
            f" ON c.id = o.contact_id WHERE c.email LIKE '%%{EMAIL_DOMAIN}'"
        )
        spread = "%s - (random() * interval '1500 days')"
        now = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE oportunitati_opportunity SET updated_at = {spread} WHERE id IN ({mine})",
                [now],
            )
            # A note is written up to a month before the opportunity's last change.
            cursor.execute(
                "UPDATE oportunitati_note n SET created_at = o.updated_at"
                " - (random() * interval '30 days') FROM oportunitati_opportunity o"
                f" WHERE o.id = n.opportunity_id AND o.id IN ({mine}) AND n.status_change = ''"
            )
            cursor.execute(
                "UPDATE oportunitati_note n SET created_at = o.updated_at"
                " FROM oportunitati_opportunity o"
                f" WHERE o.id = n.opportunity_id AND o.id IN ({mine}) AND n.status_change <> ''"
            )
            cursor.execute("ANALYZE")

        self.stdout.write(
            f"Created {len(new_contacts)} contacts, {len(new_opportunities)} opportunities, "
            f"{len(notes)} notes, {len(children)} children, {len(tasks)} tasks; "
            f"{len(new_camps)} camps with {participants} participants each."
        )

    def remove(self):
        contacts = Contact.objects.filter(email__endswith=EMAIL_DOMAIN)
        camps = Camp.objects.filter(notes=CAMP_MARKER)
        counts = (contacts.count(), camps.count())
        # Contacts first: their opportunities (and children) hold on to the camps.
        contacts.delete()
        camps.delete()
        self.stdout.write(f"Removed {counts[0]} contacts and {counts[1]} camps made by seed_load.")
