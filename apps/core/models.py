from django.conf import settings
from django.db import models
from django.utils import timezone


class TaskBase(models.Model):
    """A to-do given to a team member, attached to a camp or to an opportunity.
    Each subclass adds the link to its parent and what the shared templates need:
    get_toggle_url(), parent_label, parent_url and parent_icon."""

    title = models.CharField("ce e de făcut", max_length=300)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_tasks",
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
        abstract = True
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
