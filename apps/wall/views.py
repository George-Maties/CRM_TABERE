from django.views.generic import TemplateView

from apps.oportunitati.models import Note, Opportunity, Task


class WallView(TemplateView):
    template_name = "wall/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        visible = Opportunity.objects.visible_to(user)
        my_tasks = Task.objects.filter(assigned_to=user, done=False).select_related(
            "opportunity__contact", "created_by"
        )
        activity = (
            Note.objects.filter(opportunity__in=visible)
            .select_related("author", "opportunity__contact")
            .order_by("-created_at")[:15]
        )
        return super().get_context_data(my_tasks=my_tasks, activity=activity, **kwargs)
