from django.conf import settings
from django.db import models
from django.db.models import Count, Max, OuterRef, Subquery
from django.urls import reverse

from apps.contacte.models import Contact
from apps.tabere.models import Camp


class Status(models.TextChoices):
    NEW = "nou", "Nou"
    CALLED = "sunat", "Sunat"
    ANSWERED = "raspuns", "Răspuns"
    IN_PROGRESS = "in_lucru", "În lucru"
    WON = "castigata", "Câștigată"
    LOST = "pierduta", "Pierdută"


OPEN_STATUSES = [Status.NEW, Status.CALLED, Status.ANSWERED, Status.IN_PROGRESS]


class OpportunityQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Everything for roles with view_all_opportunities; otherwise what the user owns."""
        if user.has_perm("oportunitati.view_all_opportunities"):
            return self
        return self.filter(owner=user)

    def with_titles(self):
        """Add what `title` needs (how many opportunities each contact has) to the same query,
        so a list doesn't ask the database once per row."""
        totals = (
            self.model.objects.filter(contact=OuterRef("contact"))
            .order_by()
            .values("contact")
            .annotate(total=Count("pk"))
            .values("total")
        )
        return self.annotate(contact_total=Subquery(totals))


class Opportunity(models.Model):
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="opportunities", verbose_name="contact"
    )
    # 1, 2, 3… per contact: "Ana Pop #2". Kept when other opportunities are deleted.
    number = models.PositiveIntegerField("nr.", editable=False)
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.NEW)
    # Set when the opportunity is won: the camp the contact goes to.
    camp = models.ForeignKey(
        Camp,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="opportunities",
        verbose_name="tabără",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opportunities",
        verbose_name="responsabil",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="creată de",
    )
    created_at = models.DateTimeField("creată la", auto_now_add=True)
    updated_at = models.DateTimeField("actualizată la", auto_now=True)

    objects = OpportunityQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "oportunitate"
        verbose_name_plural = "oportunități"
        permissions = [("view_all_opportunities", "Poate vedea toate oportunitățile")]
        constraints = [
            models.UniqueConstraint(
                fields=["contact", "number"], name="unique_opportunity_number_per_contact"
            )
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.number:
            last = Opportunity.objects.filter(contact_id=self.contact_id).aggregate(Max("number"))
            self.number = (last["number__max"] or 0) + 1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("oportunitati:detail", args=[self.pk])

    @property
    def title(self):
        """The contact's name; with "#1", "#2"… when the contact has more than one opportunity."""
        total = getattr(self, "contact_total", None)
        if total is None:
            total = Opportunity.objects.filter(contact_id=self.contact_id).count()
        if total > 1:
            return f"{self.contact.name} #{self.number}"
        return self.contact.name

    def change_status(self, new_status, user, comment, camp=None):
        """Set the status and record it, with the required comment, in the notes.
        Winning needs the camp the contact joins; leaving "won" takes them out of it."""
        if new_status == Status.WON and camp is None:
            raise ValueError("A won opportunity needs a camp.")
        change = f"{self.get_status_display()} → {Status(new_status).label}"
        self.status = new_status
        self.camp = camp if new_status == Status.WON else None
        if self.camp:
            change += f" · {self.camp.name}"
        self.save(update_fields=["status", "camp", "updated_at"])
        self.notes.create(author=user, status_change=change, text=comment)

    def touch(self):
        """Mark the opportunity as just updated (new note)."""
        self.save(update_fields=["updated_at"])


class Note(models.Model):
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="notes", verbose_name="oportunitate"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        verbose_name="autor",
    )
    text = models.TextField("notă")
    # "Nou → Sunat" when the note records a status change; its text is the required comment.
    status_change = models.CharField("schimbare de status", max_length=300, blank=True)
    created_at = models.DateTimeField("scrisă la", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notă"
        verbose_name_plural = "note"

    def __str__(self):
        return self.text[:60]
