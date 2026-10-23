from datetime import timedelta

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Case, Q, Value, When
from django.urls import reverse
from django.utils import formats, timezone

from apps.core.models import TaskBase


class CampStatus(models.TextChoices):
    """Where a camp is, worked out from its dates (never saved, so it moves on by itself)."""

    PREPARING = "in_lucru", "În lucru"
    FINAL_DETAILS = "ultimele_detalii", "Ultimele detalii"
    RUNNING = "in_desfasurare", "În desfășurare"
    FINISHED = "finalizata", "Finalizată"


# From this many days before the start, a camp is in its final details
FINAL_DETAILS_DAYS = 14

# Bootstrap color of each status badge
CAMP_STATUS_COLORS = {
    CampStatus.PREPARING: "primary",
    CampStatus.FINAL_DETAILS: "warning",
    CampStatus.RUNNING: "success",
    CampStatus.FINISHED: "secondary",
}


class CampQuerySet(models.QuerySet):
    def with_status(self):
        """Add `period_status` (a CampStatus value), so camps can be filtered and counted by it."""
        today = timezone.localdate()
        return self.annotate(
            period_status=Case(
                When(
                    start_date__gt=today + timedelta(days=FINAL_DETAILS_DAYS),
                    then=Value(CampStatus.PREPARING),
                ),
                When(start_date__gt=today, then=Value(CampStatus.FINAL_DETAILS)),
                # A camp without an end date lasts one day.
                When(
                    Q(end_date__gte=today) | Q(end_date__isnull=True, start_date=today),
                    then=Value(CampStatus.RUNNING),
                ),
                default=Value(CampStatus.FINISHED),
            )
        )


class Camp(models.Model):
    name = models.CharField("nume", max_length=200)
    start_date = models.DateField("începe pe")
    end_date = models.DateField("se termină pe", null=True, blank=True)
    # Where the children stay, from the Cazări list (which also has the town)
    accommodation = models.ForeignKey(
        "cazari.Accommodation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="camps",
        verbose_name="cazare",
    )
    notes = models.TextField("observații", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="creată de",
    )
    created_at = models.DateTimeField("creată la", auto_now_add=True)

    objects = CampQuerySet.as_manager()

    class Meta:
        ordering = ["-start_date", "name"]
        verbose_name = "tabără"
        verbose_name_plural = "tabere"

    def __str__(self):
        return f"{self.name} ({formats.date_format(self.start_date, 'j M Y').lower()})"

    def get_absolute_url(self):
        return reverse("tabere:detail", args=[self.pk])

    @property
    def status(self):
        """In work until 14 days before the start, then final details, running, finished."""
        today = timezone.localdate()
        days_left = (self.start_date - today).days
        if days_left > FINAL_DETAILS_DAYS:
            return CampStatus.PREPARING
        if days_left > 0:
            return CampStatus.FINAL_DETAILS
        if (self.end_date or self.start_date) >= today:
            return CampStatus.RUNNING
        return CampStatus.FINISHED

    @property
    def status_label(self):
        return CampStatus(self.status).label

    @property
    def status_color(self):
        return CAMP_STATUS_COLORS[self.status]


class Task(TaskBase):
    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="tasks", verbose_name="tabără"
    )

    class Meta(TaskBase.Meta):
        pass

    def get_toggle_url(self):
        return reverse("tabere:task-toggle", args=[self.pk])

    @property
    def parent_label(self):
        return self.camp.name

    @property
    def parent_url(self):
        return f"{self.camp.get_absolute_url()}#sarcini"

    parent_icon = "bi-backpack"


class Child(models.Model):
    """A child who comes to camp: listed on the camp page under the contact (the parent or
    teacher) whose won opportunity brought them."""

    opportunity = models.ForeignKey(
        "oportunitati.Opportunity",
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="oportunitate",
    )
    name = models.CharField("numele copilului", max_length=200)
    # Required in the form; empty only for children added before the age was asked
    age = models.PositiveSmallIntegerField(
        "vârsta",
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
    )
    city = models.CharField("oraș", max_length=200, blank=True)
    # Medical data about a minor: shown only to whoever works the contact (see the camp page).
    medical_notes = models.TextField("probleme medicale", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        verbose_name="adăugat de",
    )
    created_at = models.DateTimeField("adăugat la", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "copil"
        verbose_name_plural = "copii"

    def __str__(self):
        return self.name
