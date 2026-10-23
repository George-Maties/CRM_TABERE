from django.db.models import Count, F
from django.views.generic import TemplateView

from apps.oportunitati.models import Note, Opportunity
from apps.oportunitati.models import Task as OpportunityTask
from apps.tabere.models import Task as CampTask

# How many entries "Activitate recentă" shows; older ones stay in each opportunity's history.
RECENT_ACTIVITY = 20


def add_titles(opportunities):
    """Load what the titles need ("Ana Pop #2") in one query, instead of one per opportunity."""
    totals = dict(
        Opportunity.objects.filter(contact__in={o.contact_id for o in opportunities})
        .order_by()
        .values_list("contact")
        .annotate(Count("pk"))
    )
    for opportunity in opportunities:
        opportunity.contact_total = totals[opportunity.contact_id]


def group_by_parent(tasks):
    """Tasks of the same camp or opportunity together, under it. The group with the most
    urgent task comes first (tasks arrive sorted by deadline)."""
    groups = {}
    for task in tasks:
        key = task.parent_url
        if key not in groups:
            groups[key] = {
                "label": task.parent_label,
                "url": task.parent_url,
                "icon": task.parent_icon,
                "tasks": [],
            }
        groups[key]["tasks"].append(task)
    return list(groups.values())


# Earliest deadline first; tasks without one after those with
BY_DEADLINE = [F("due_date").asc(nulls_last=True), "created_at"]


class WallView(TemplateView):
    template_name = "wall/index.html"

    def get_context_data(self, **kwargs):
        user = self.request.user
        # Sellers: what happens on their own opportunities; founders and admins: everything.
        visible = Opportunity.objects.visible_to(user)
        camp_tasks = list(
            CampTask.objects.filter(assigned_to=user, done=False)
            .select_related("camp", "created_by")
            .order_by(*BY_DEADLINE)
        )
        opportunity_tasks = list(
            OpportunityTask.objects.filter(assigned_to=user, done=False)
            .select_related("opportunity__contact", "created_by")
            .order_by(*BY_DEADLINE)
        )
        activity = list(
            Note.objects.filter(opportunity__in=visible)
            .select_related("author", "opportunity__contact")
            .order_by("-created_at", "-pk")[:RECENT_ACTIVITY]
        )
        add_titles([task.opportunity for task in opportunity_tasks])
        add_titles([note.opportunity for note in activity])
        return super().get_context_data(
            camp_tasks=camp_tasks,
            camp_task_groups=group_by_parent(camp_tasks),
            opportunity_tasks=opportunity_tasks,
            opportunity_task_groups=group_by_parent(opportunity_tasks),
            activity=activity,
            sees_all_activity=user.has_perm("oportunitati.view_all_opportunities"),
            **kwargs,
        )
