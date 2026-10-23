from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from apps.contacte.models import Contact


class Status(models.TextChoices):
    NEW = "nou", "Nou"
    CALLED = "sunat", "Sunat"
    ANSWERED = "raspuns", "Răspuns"
    IN_PROGRESS = "in_lucru", "În lucru"
    WON = "hotarat", "Hotărât"
    LOST = "refuzat", "Refuzat / neinteresat"


class OpportunityQuerySet(models.QuerySet):
    def visible_to(self, user):
        """Everything for roles with view_all_opportunities; otherwise what the user owns
        or has a task on (so a task assigned by someone else can always be opened)."""
        if user.has_perm("oportunitati.view_all_opportunities"):
            return self
        return self.filter(Q(owner=user) | Q(tasks__assigned_to=user)).distinct()


class Opportunity(models.Model):
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="opportunities", verbose_name="contact"
    )
    title = models.CharField("titlu", max_length=200)
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.NEW)
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

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("oportunitati:detail", args=[self.pk])

    def change_status(self, new_status, user):
        """Set the status and record the change in the notes. Returns False if unchanged."""
        if new_status == self.status:
            return False
        old_label = self.get_status_display()
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        self.notes.create(
            author=user,
            is_status_change=True,
            text=f"{old_label} → {self.get_status_display()}",
        )
        return True

    def touch(self):
        """Mark the opportunity as just updated (new note, new task)."""
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
    is_status_change = models.BooleanField("schimbare de status", default=False)
    created_at = models.DateTimeField("scrisă la", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notă"
        verbose_name_plural = "note"

    def __str__(self):
        return self.text[:60]


class Task(models.Model):
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, related_name="tasks", verbose_name="oportunitate"
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
