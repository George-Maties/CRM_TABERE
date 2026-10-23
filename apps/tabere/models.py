from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import formats

from apps.core.models import TaskBase


class Camp(models.Model):
    name = models.CharField("nume", max_length=200)
    start_date = models.DateField("începe pe")
    end_date = models.DateField("se termină pe", null=True, blank=True)
    location = models.CharField("locație", max_length=200, blank=True)
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
