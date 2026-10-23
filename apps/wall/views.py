from django.db.models import Count
from django.views.generic import TemplateView

from apps.oportunitati.models import Note, Opportunity
from apps.tabere.models import Task


class WallView(TemplateView):
    template_name = "wall/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        visible = Opportunity.objects.visible_to(user)
        my_tasks = Task.objects.filter(assigned_to=user, done=False).select_related(
            "camp", "created_by"
        )
        activity = list(
            Note.objects.filter(opportunity__in=visible)
            .select_related("author", "opportunity__contact")
            .order_by("-created_at")[:15]
        )
        # What the opportunity titles need ("Ana Pop #2"), in one query instead of one per note
        totals = dict(
            Opportunity.objects.filter(
                contact__in={note.opportunity.contact_id for note in activity}
            )
            .order_by()
            .values_list("contact")
            .annotate(Count("pk"))
        )
        for note in activity:
            note.opportunity.contact_total = totals[note.opportunity.contact_id]
        return super().get_context_data(my_tasks=my_tasks, activity=activity, **kwargs)
