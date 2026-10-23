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
        with_my_opportunities = self.model.objects.filter(opportunities__owner=user).values("pk")
        return self.filter(Q(assigned_to=user) | Q(pk__in=with_my_opportunities))

    def assign(self, user, move_open_opportunities=True):
        """Give these contacts to `user`. Their open opportunities can follow,
        so the new seller sees and continues them. Returns how many contacts were assigned."""
        # Imported here: opportunities depend on contacts, not the other way round.
        from apps.oportunitati.models import OPEN_STATUSES, Opportunity

        if move_open_opportunities:
            Opportunity.objects.filter(contact__in=self, status__in=OPEN_STATUSES).update(
                owner=user
            )
        return self.update(assigned_to=user)


class Contact(models.Model):
    class Kind(models.TextChoices):
        PARENT = "parinte", "Părinte"
        SCHOOL = "scoala", "Școală"
        TEACHER = "profesor", "Profesor"
        COMPANY = "firma", "Firmă"
        OTHER = "altul", "Altul"

    name = models.CharField("nume", max_length=200)
    kind = models.CharField("tip", max_length=20, choices=Kind.choices, default=Kind.PARENT)
    phone = models.CharField("telefon", max_length=30, blank=True)
    email = models.EmailField("email", blank=True)
    notes = models.TextField("observații", blank=True)
    # The seller who works this contact; sellers see only the contacts assigned to them.
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
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
