from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse


class ContactQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Everything for roles with view_all_contacts; otherwise the contacts assigned to the
        user, plus those of their own opportunities (so an opportunity never links to a 404)."""
        if user.has_perm("contacte.view_all_contacts"):
            return self
        mine = self.model.objects.filter(Q(assignees=user) | Q(opportunities__owner=user))
        return self.filter(pk__in=mine.values("pk"))

    def assign(self, users):
        """Make `users` the people who work these contacts, in place of whoever did.
        Returns how many contacts were assigned."""
        through = self.model.assignees.through
        contact_ids = list(self.values_list("pk", flat=True))
        through.objects.filter(contact_id__in=contact_ids).delete()
        through.objects.bulk_create(
            through(contact_id=contact_id, user_id=user.pk)
            for contact_id in contact_ids
            for user in users
        )
        return len(contact_ids)


class Contact(models.Model):
    class Kind(models.TextChoices):
        PARENT = "parinte", "Părinte"
        TEACHER = "profesor", "Profesor"

    name = models.CharField("nume", max_length=200)
    kind = models.CharField("tip", max_length=20, choices=Kind.choices, default=Kind.PARENT)
    phone = models.CharField("telefon", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    notes = models.TextField("observații", blank=True)
    # Who works this contact, usually one seller; sellers see only the contacts assigned to them.
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="assigned_contacts",
        verbose_name="atribuit lui",
    )
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

    objects = ContactQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        verbose_name = "contact"
        verbose_name_plural = "contacte"
        permissions = [
            ("view_all_contacts", "Poate vedea toate contactele"),
            ("assign_contact", "Poate atribui contacte"),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("contacte:detail", args=[self.pk])
