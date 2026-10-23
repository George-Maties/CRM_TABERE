from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.contacte.models import Contact
from apps.oportunitati.models import Opportunity, Status

from .forms import CampForm, ChildForm, TaskForm
from .models import Camp, CampStatus, Child, Task


class CampListView(PermissionRequiredMixin, ListView):
    permission_required = "tabere.view_camp"
    model = Camp
    template_name = "tabere/list.html"

    def get_queryset(self):
        camps = Camp.objects.with_status().select_related("accommodation")
        self.query = self.request.GET.get("q", "").strip()
        self.status = self.request.GET.get("status", "")
        if self.query:
            camps = camps.filter(
                Q(name__icontains=self.query)
                | Q(accommodation__name__icontains=self.query)
                | Q(accommodation__city__icontains=self.query)
            )
        # The tabs count with the search but not with the status they filter.
        self.counts = dict(
            camps.order_by().values_list("period_status").annotate(total=Count("id"))
        )
        if self.status in CampStatus.values:
            camps = camps.filter(period_status=self.status)
        return camps.annotate(
            participant_count=Count("opportunities", filter=Q(opportunities__status=Status.WON))
        )

    def get_context_data(self, **kwargs):
        total = sum(self.counts.values())
        status_tabs = [
            {"value": None, "label": "Toate", "count": total, "active": not self.status}
        ] + [
            {
                "value": value,
                "label": label,
                "count": self.counts.get(value, 0),
                "active": value == self.status,
            }
            for value, label in CampStatus.choices
        ]
        return super().get_context_data(
            query=self.query, status=self.status, status_tabs=status_tabs, **kwargs
        )


class CampDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "tabere.view_camp"
    model = Camp
    template_name = "tabere/detail.html"

    def get_context_data(self, **kwargs):
        participants = list(
            self.object.opportunities.filter(status=Status.WON)
            .select_related("contact", "owner", "camp")
            .prefetch_related("children")
            .with_titles()
        )
        visible_ids = set(
            Opportunity.objects.visible_to(self.request.user)
            .filter(camp=self.object)
            .values_list("pk", flat=True)
        )
        for opportunity in participants:
            # Only who works the opportunity opens it and adds or removes its children.
            opportunity.can_edit = opportunity.pk in visible_ids
        child_count = sum(len(opportunity.children.all()) for opportunity in participants)
        adult_count = sum(opportunity.contact_goes for opportunity in participants)
        visible_contact_ids = set(
            Contact.objects.visible_to(self.request.user)
            .filter(opportunities__camp=self.object)
            .values_list("pk", flat=True)
        )
        context = {
            "participants": participants,
            "visible_ids": visible_ids,
            "visible_contact_ids": visible_contact_ids,
            # Seats taken: the children, plus the parents and teachers who come along
            "child_count": child_count,
            "adult_count": adult_count,
            "people_count": child_count + adult_count,
            # The participant whose "+" form came back with errors, opened again
            "child_form": None,
            "child_form_for": None,
            "tasks": self.object.tasks.select_related("assigned_to", "created_by"),
            "task_form": TaskForm(initial={"assigned_to": self.request.user}),
        }
        context.update(kwargs)
        return super().get_context_data(**context)


class CampCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "tabere.add_camp"
    model = Camp
    form_class = CampForm
    template_name = "tabere/form.html"
    success_message = "Tabăra „%(name)s” a fost creată."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CampUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "tabere.change_camp"
    model = Camp
    form_class = CampForm
    template_name = "tabere/form.html"
    success_message = "Modificările au fost salvate."


class CampDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    permission_required = "tabere.delete_camp"
    model = Camp
    template_name = "tabere/confirm_delete.html"
    success_url = reverse_lazy("tabere:list")
    success_message = "Tabăra a fost ștearsă."

    def form_valid(self, form):
        # Won opportunities point at their camp; deleting it would lose where children go.
        if self.object.opportunities.exists():
            messages.error(
                self.request, "Tabăra are participanți și nu poate fi ștearsă. Mutați-i întâi."
            )
            return redirect(self.object)
        return super().form_valid(form)


class TaskCreateView(PermissionRequiredMixin, View):
    permission_required = "tabere.add_task"
    http_method_names = ["post"]

    def post(self, request, pk):
        camp = get_object_or_404(Camp, pk=pk)
        form = TaskForm(request.POST)
        if not form.is_valid():
            # Show the camp page again, with the errors next to the task form.
            page = CampDetailView(request=request, kwargs={"pk": pk})
            page.object = camp
            return page.render_to_response(page.get_context_data(task_form=form))
        form.instance.camp = camp
        form.instance.created_by = request.user
        task = form.save()
        assignee = task.assigned_to.get_full_name() or task.assigned_to.get_username()
        messages.success(request, f"Sarcina a fost atribuită lui {assignee}.")
        return redirect(f"{camp.get_absolute_url()}#sarcini")


class TaskToggleView(PermissionRequiredMixin, View):
    permission_required = "tabere.change_task"
    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        task.toggle_done()
        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(f"{task.camp.get_absolute_url()}#sarcini")


def participant_for(user, pk):
    """A won opportunity (a contact in a camp) the user works, or a 404: children are added
    and removed only under one's own contacts (everyone's, for roles that see everything)."""
    participants = Opportunity.objects.visible_to(user).filter(
        status=Status.WON, camp__isnull=False
    )
    return get_object_or_404(participants.select_related("camp", "contact"), pk=pk)


class ChildCreateView(PermissionRequiredMixin, View):
    permission_required = "tabere.add_child"
    http_method_names = ["post"]

    def post(self, request, pk):
        opportunity = participant_for(request.user, pk)
        camp = opportunity.camp
        form = ChildForm(request.POST)
        if not form.is_valid():
            # Show the camp page again, with the form open under that contact.
            page = CampDetailView(request=request, kwargs={"pk": camp.pk})
            page.object = camp
            return page.render_to_response(
                page.get_context_data(child_form=form, child_form_for=opportunity.pk)
            )
        form.instance.opportunity = opportunity
        form.instance.created_by = request.user
        child = form.save()
        messages.success(
            request, f"{child.name} a fost adăugat la {opportunity.contact.name}, în „{camp.name}”."
        )
        return redirect(f"{camp.get_absolute_url()}#participant-{opportunity.pk}")


class ChildDeleteView(PermissionRequiredMixin, View):
    permission_required = "tabere.delete_child"
    http_method_names = ["post"]

    def post(self, request, pk):
        child = get_object_or_404(Child.objects.select_related("opportunity"), pk=pk)
        opportunity = participant_for(request.user, child.opportunity_id)
        child.delete()
        messages.success(request, f"{child.name} a fost scos din tabără.")
        return redirect(f"{opportunity.camp.get_absolute_url()}#participant-{opportunity.pk}")


class ParticipantGoesView(PermissionRequiredMixin, View):
    """The "Merge în tabără" tick of a participant: the contact comes to the camp too."""

    permission_required = "oportunitati.change_opportunity"
    http_method_names = ["post"]

    def post(self, request, pk):
        opportunity = participant_for(request.user, pk)
        opportunity.contact_goes = request.POST.get("contact_goes") == "1"
        if not opportunity.contact_goes:
            # Not coming any more: their bed is free again.
            opportunity.contact_room = None
        opportunity.save(update_fields=["contact_goes", "contact_room", "updated_at"])
        name = opportunity.contact.name
        verb = "merge" if opportunity.contact_goes else "nu mai merge"
        messages.success(request, f"{name} {verb} în „{opportunity.camp.name}”.")
        return redirect(f"{opportunity.camp.get_absolute_url()}#participant-{opportunity.pk}")
