from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import formats

from apps.core.models import TaskBase


class Camp(models.Model):
    name = models.CharField("nume", max_length=200)
    start_date = models.DateField("începe pe")
    end_date = models.DateField("se termină pe", null=True, blank=True)
    # Where the children stay (the guesthouse) and the town it is in
    accommodation = models.CharField("cazare", max_length=200, blank=True)
    location = models.CharField("oraș", max_length=200, blank=True)
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

    class Meta:
        ordering = ["-start_date", "name"]
        verbose_name = "tabără"
        verbose_name_plural = "tabere"

    def __str__(self):
        return f"{self.name} ({formats.date_format(self.start_date, 'j M Y').lower()})"

    def get_absolute_url(self):
        return reverse("tabere:detail", args=[self.pk])


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
