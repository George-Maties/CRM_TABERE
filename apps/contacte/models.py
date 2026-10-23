from django.conf import settings
from django.db import models
from django.urls import reverse


class Contact(models.Model):
    class Kind(models.TextChoices):
        PARENT = "parinte", "Părinte"
        SCHOOL = "scoala", "Școală"
        COMPANY = "firma", "Firmă"
        OTHER = "altul", "Altul"

    name = models.CharField("nume", max_length=200)
    kind = models.CharField("tip", max_length=20, choices=Kind.choices, default=Kind.PARENT)
    phone = models.CharField("telefon", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    notes = models.TextField("observații", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="adăugat de",
    )
    created_at = models.DateTimeField("adăugat la", auto_now_add=True)
    updated_at = models.DateTimeField("actualizat la", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "contact"
        verbose_name_plural = "contacte"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contacte:detail", args=[self.pk])
