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

from .forms import CampForm, TaskForm
from .models import Camp, Task


class CampListView(PermissionRequiredMixin, ListView):
    permission_required = "tabere.view_camp"
    model = Camp
    template_name = "tabere/list.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                participant_count=Count("opportunities", filter=Q(opportunities__status=Status.WON))
            )
        )


class CampDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "tabere.view_camp"
    model = Camp
    template_name = "tabere/detail.html"

    def get_context_data(self, **kwargs):
        participants = (
            self.object.opportunities.filter(status=Status.WON)
            .select_related("contact", "owner")
            .with_titles()
        )
        visible_ids = set(
            Opportunity.objects.visible_to(self.request.user)
            .filter(camp=self.object)
            .values_list("pk", flat=True)
        )
        visible_contact_ids = set(
            Contact.objects.visible_to(self.request.user)
            .filter(opportunities__camp=self.object)
            .values_list("pk", flat=True)
        )
        context = {
            "participants": participants,
            "visible_ids": visible_ids,
            "visible_contact_ids": visible_contact_ids,
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
