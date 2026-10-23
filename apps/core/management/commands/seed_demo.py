from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.roles import FOUNDER, SELLER
from apps.contacte.models import Contact
from apps.oportunitati.models import Note, Opportunity, Status, Task

# Demo contacts are recognised by this e-mail domain, so --reset never touches real data.
DEMO_DOMAIN = "@example.com"

CONTACTS = [
    ("Andreea Ionescu", Contact.Kind.PARENT, "0700 100 201", "andreea.ionescu"),
    ("Mihai Popa", Contact.Kind.PARENT, "0700 100 202", "mihai.popa"),
    (
        "Școala Gimnazială nr. 12 Brașov",
        Contact.Kind.SCHOOL,
        "0700 100 203",
        "secretariat.scoala12",
    ),
    ("Elena Dumitrescu", Contact.Kind.PARENT, "0700 100 204", "elena.dumitrescu"),
    (
        "Liceul Teoretic „Mihai Eminescu” Cluj",
        Contact.Kind.SCHOOL,
        "0700 100 205",
        "liceul.eminescu",
    ),
    ("Softwave SRL", Contact.Kind.COMPANY, "0700 100 206", "hr.softwave"),
    ("Cristina Stan", Contact.Kind.PARENT, "0700 100 207", "cristina.stan"),
    ("Radu Georgescu", Contact.Kind.PARENT, "0700 100 208", "radu.georgescu"),
    ("Asociația Părinților Sector 3", Contact.Kind.OTHER, "0700 100 209", "contact.aps3"),
    ("Ioana Marinescu", Contact.Kind.PARENT, "0700 100 210", "ioana.marinescu"),
]

# contact index, title, status, owner ("seller"/"founder"), days since last activity, notes
OPPORTUNITIES = [
    (
        0,
        "Tabăra de vară 2027, 2 copii (9 și 11 ani)",
        Status.IN_PROGRESS,
        "seller",
        1,
        [
            (
                "seller",
                "Mama vrea tabăra de la munte, 7 zile, în iulie. Întreabă de reducerea la frați.",
            ),
            (
                "seller",
                "I-am explicat reducerea de 10% pentru al doilea copil. Așteaptă oferta pe email.",
            ),
        ],
    ),
    (
        1,
        "Tabără de iarnă 2027",
        Status.CALLED,
        "seller",
        2,
        [
            ("seller", "Nu a răspuns. Revin mâine după-amiază."),
        ],
    ),
    (
        2,
        "Excursie clasa a V-a, 28 de elevi",
        Status.ANSWERED,
        "founder",
        3,
        [
            (
                "founder",
                "Am vorbit cu doamna dirigintă. Vor 3 zile în mai, buget de circa 900 lei de elev.",
            ),
        ],
    ),
    (
        3,
        "Tabăra de vară 2026",
        Status.WON,
        "seller",
        40,
        [
            ("seller", "A confirmat pentru seria 2. Avansul a fost plătit."),
        ],
    ),
    (4, "Tabără de vară cu limba engleză, 40 de elevi", Status.NEW, "founder", 0, []),
    (
        5,
        "Tabără pentru copiii angajaților",
        Status.IN_PROGRESS,
        "founder",
        1,
        [
            (
                "founder",
                "HR-ul vrea o propunere pentru 25 de copii, august. Decid în două săptămâni.",
            ),
        ],
    ),
    (
        6,
        "Tabăra de vară 2027",
        Status.LOST,
        "seller",
        10,
        [
            ("seller", "A ales o tabără mai aproape de casă. Rămâne în lista pentru anul viitor."),
        ],
    ),
    (
        7,
        "Tabără de schi, 1 copil",
        Status.ANSWERED,
        "seller",
        4,
        [
            (
                "seller",
                "Interesat de săptămâna 10–16 februarie. Întreabă dacă echipamentul e inclus.",
            ),
        ],
    ),
    (
        9,
        "Tabăra de vară 2026",
        Status.WON,
        "seller",
        60,
        [
            ("seller", "Confirmat. Copilul a mai fost la noi și anul trecut."),
        ],
    ),
    (9, "Tabăra de vară 2027", Status.NEW, "seller", 0, []),
]

# opportunity index, task, assignee, created by, due in days (None = no date), done
TASKS = [
    (0, "Trimite oferta pentru tabăra de la munte", "seller", "founder", 2, False),
    (1, "Sună din nou", "seller", "seller", -1, False),
    (2, "Pregătește oferta de grup pentru 28 de elevi", "seller", "founder", 5, False),
    (5, "Discuție cu HR despre program și transport", "founder", "founder", 1, False),
    (5, "Trimite prezentarea taberelor", "founder", "founder", -3, True),
    (7, "Verifică dacă închirierea echipamentului e inclusă", "founder", "seller", 3, False),
]


class Command(BaseCommand):
    help = (
        f"Add 10 demo contacts with opportunities, notes and tasks (e-mails end in {DEMO_DOMAIN})."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true", help="Delete the existing demo data first."
        )

    @transaction.atomic
    def handle(self, *args, reset, **options):
        demo = Contact.objects.filter(email__endswith=DEMO_DOMAIN)
        if demo.exists():
            if not reset:
                raise CommandError("Demo data already exists. Use --reset to recreate it.")
            demo.delete()

        people = {"founder": self.member_of(FOUNDER), "seller": self.member_of(SELLER)}
        now = timezone.now()
        today = timezone.localdate()

        contacts = [
            Contact.objects.create(
                name=name,
                kind=kind,
                phone=phone,
                email=f"{email}{DEMO_DOMAIN}",
                created_by=people["seller"],
            )
            for name, kind, phone, email in CONTACTS
        ]

        opportunities = []
        for contact_index, title, status, owner, days_ago, notes in OPPORTUNITIES:
            opportunity = Opportunity.objects.create(
                contact=contacts[contact_index],
                title=title,
                status=status,
                owner=people[owner],
                created_by=people[owner],
            )
            when = now - timedelta(days=days_ago)
            for offset, (author, text) in enumerate(reversed(notes)):
                note = opportunity.notes.create(author=people[author], text=text)
                Note.objects.filter(pk=note.pk).update(
                    created_at=when - timedelta(hours=offset * 5)
                )
            # Timestamps are set after saving: auto_now fields ignore values passed to create().
            Opportunity.objects.filter(pk=opportunity.pk).update(
                created_at=when - timedelta(days=2), updated_at=when
            )
            opportunities.append(opportunity)

        for index, title, assignee, creator, due_in, done in TASKS:
            Task.objects.create(
                opportunity=opportunities[index],
                title=title,
                assigned_to=people[assignee],
                created_by=people[creator],
                due_date=today + timedelta(days=due_in) if due_in is not None else None,
                done=done,
                done_at=now if done else None,
            )

        note_count = Note.objects.filter(opportunity__in=opportunities).count()
        self.stdout.write(
            f"Created {len(contacts)} contacts, {len(opportunities)} opportunities, "
            f"{note_count} notes, {len(TASKS)} tasks."
        )

    def member_of(self, role):
        """First active user with the role; falls back to a superuser so the demo always runs."""
        users = get_user_model().objects.filter(is_active=True)
        user = users.filter(groups__name=role).order_by("id").first()
        if user is None:
            user = users.filter(is_superuser=True).order_by("id").first()
        if user is None:
            raise CommandError(f"No user with role {role!r} and no superuser. Create one first.")
        return user
