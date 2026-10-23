from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import formats, timezone


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


class Task(models.Model):
    camp = models.ForeignKey(
        Camp, on_delete=models.CASCADE, related_name="tasks", verbose_name="tabără"
    )
    title = models.CharField("ce e de făcut", max_length=300)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tasks",
        verbose_name="atribuită lui",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
        verbose_name="creată de",
    )
    due_date = models.DateField("termen", null=True, blank=True)
    done = models.BooleanField("gata", default=False)
    done_at = models.DateTimeField("terminată la", null=True, blank=True)
    created_at = models.DateTimeField("creată la", auto_now_add=True)

    class Meta:
        ordering = ["done", "due_date", "created_at"]
        verbose_name = "sarcină"
        verbose_name_plural = "sarcini"

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return not self.done and self.due_date is not None and self.due_date < timezone.localdate()

    def toggle_done(self):
        self.done = not self.done
        self.done_at = timezone.now() if self.done else None
        self.save(update_fields=["done", "done_at"])
