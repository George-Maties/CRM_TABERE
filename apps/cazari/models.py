from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Accommodation(models.Model):
    """A guesthouse or hotel where camps stay; each camp picks one from this list."""

    name = models.CharField("nume", max_length=200)
    city = models.CharField("oraș", max_length=200, blank=True)
    # Required in the form; 0 only for places carried over from camps before this list existed
    capacity = models.PositiveIntegerField("număr de locuri", validators=[MinValueValidator(1)])
    contact_name = models.CharField("persoană de contact", max_length=200, blank=True)
    phone = models.CharField("telefon", max_length=30, blank=True)
    created_at = models.DateTimeField("adăugată la", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "cazare"
        verbose_name_plural = "cazări"

    def __str__(self):
        return f"{self.name}, {self.city}" if self.city else self.name

    def get_absolute_url(self):
        return reverse("cazari:update", args=[self.pk])
