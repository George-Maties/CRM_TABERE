from django.conf import settings
from django.db import models
from django.db.models import Count, Max, OuterRef, Subquery
from django.urls import reverse

from apps.contacte.models import Contact
from apps.core.models import TaskBase
from apps.tabere.models import Camp


class Status(models.TextChoices):
    # Being worked on, from the first call until it is won or lost
    POTENTIAL = "potential", "Potențial"
    WON = "castigata", "Câștigat"
    LOST = "pierduta", "Pierdut"


# Final: a won or lost opportunity never becomes potential again; a new one is created instead.
CLOSED_STATUSES = [Status.WON, Status.LOST]


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
    status = models.CharField(
        "status", max_length=20, choices=Status.choices, default=Status.POTENTIAL
    )
    # Set when the opportunity is won: the camp the contact goes to.
    camp = models.ForeignKey(
        Camp,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="opportunities",
        verbose_name="tabără",
    )
    # The parent or teacher comes to the camp too (with the children), taking a seat.
    contact_goes = models.BooleanField("merge în tabără", default=False)
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

    def change_status(self, new_status, user, reason="", camp=None):
        """Set the status and record the change in the history; a reason (required when
        losing) goes in just before it, as an ordinary note.
        Winning needs the camp the contact joins; leaving "won" takes them out of it.
        The seller stays responsible whatever the status."""
        if new_status == Status.WON and camp is None:
            raise ValueError("A won opportunity needs a camp.")
        if self.is_closed and new_status == Status.POTENTIAL:
            raise ValueError("A won or lost opportunity can't become potential again.")
        change = f"{self.get_status_display()} → {Status(new_status).label}"
        self.status = new_status
        self.camp = camp if new_status == Status.WON else None
        if self.camp:
            change += f" · {self.camp.name}"
        self.save(update_fields=["status", "camp", "updated_at"])
        if reason:
            self.notes.create(author=user, text=reason)
        self.notes.create(author=user, status_change=change, new_status=new_status)

    @property
    def is_closed(self):
        return self.status in CLOSED_STATUSES

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
    # Empty for a status change, which is its own entry in the history.
    text = models.TextField("notă", blank=True)
    # "Potențial → Pierdut" when the entry records a status change, and the status it led to.
    status_change = models.CharField("schimbare de status", max_length=300, blank=True)
    new_status = models.CharField("status nou", max_length=20, choices=Status.choices, blank=True)
    created_at = models.DateTimeField("scrisă la", auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "notă"
        verbose_name_plural = "note"

    def __str__(self):
        return self.status_change or self.text[:60]


class Task(TaskBase):
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="tasks", verbose_name="oportunitate"
    )

    class Meta(TaskBase.Meta):
        pass

    def get_toggle_url(self):
        return reverse("oportunitati:task-toggle", args=[self.pk])

    @property
    def parent_label(self):
        return self.opportunity.title

    @property
    def parent_url(self):
        return f"{self.opportunity.get_absolute_url()}#sarcini"

    parent_icon = "bi-briefcase"
