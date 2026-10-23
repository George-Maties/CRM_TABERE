from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.roles import sellers_and_founders
from apps.contacte.models import Contact
from apps.core.templatetags.ui import display_name

from .forms import NoteForm, OpportunityForm, StatusForm, TaskForm
from .models import Opportunity, Status, Task


class VisibleOpportunityMixin:
    """Limit every view to the opportunities the user may see; others answer 404."""

    def get_queryset(self):
        return (
            Opportunity.objects.visible_to(self.request.user)
            .select_related("contact", "owner")
            .with_titles()
        )


class OpportunityListView(PermissionRequiredMixin, VisibleOpportunityMixin, ListView):
    permission_required = "oportunitati.view_opportunity"
    paginate_by = 25
    template_name = "oportunitati/list.html"

    def get_queryset(self):
        opportunities = super().get_queryset()
        self.query = self.request.GET.get("q", "").strip()
        self.status = self.request.GET.get("status", "")
        self.can_see_all = self.request.user.has_perm("oportunitati.view_all_opportunities")
        # Seller filter: only for roles that see everyone's opportunities
        self.owner = self.request.GET.get("responsabil", "") if self.can_see_all else ""
        if self.query:
            opportunities = opportunities.filter(contact__name__icontains=self.query)
        # Each row of tabs counts with the other row's filter but not its own,
        # so every tab shows how many it would list.
        by_owner = opportunities.filter(owner=self.owner) if self.owner.isdigit() else opportunities
        by_status = (
            opportunities.filter(status=self.status)
            if self.status in Status.values
            else opportunities
        )
        self.counts = self.count_by(by_owner, "status")
        self.owner_counts = self.count_by(by_status, "owner") if self.can_see_all else {}
        if self.status in Status.values:
            return by_owner.filter(status=self.status)
        return by_owner

    @staticmethod
    def count_by(opportunities, field):
        return dict(opportunities.order_by().values_list(field).annotate(total=Count("id")))

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
            for value, label in Status.choices
        ]
        owner_tabs = [
            {
                "value": str(person.pk),
                "label": display_name(person),
                "count": self.owner_counts.get(person.pk, 0),
                "active": str(person.pk) == self.owner,
            }
            for person in (sellers_and_founders() if self.can_see_all else [])
        ]
        return super().get_context_data(
            query=self.query,
            owner=self.owner,
            owner_tabs=owner_tabs,
            status=self.status,
            status_tabs=status_tabs,
            total=total,
            can_see_all=self.can_see_all,
            **kwargs,
        )


class OpportunityDetailView(PermissionRequiredMixin, VisibleOpportunityMixin, DetailView):
    permission_required = "oportunitati.view_opportunity"
    template_name = "oportunitati/detail.html"

    def get_context_data(self, **kwargs):
        context = {
            "status_form": StatusForm(opportunity=self.object, user=self.request.user),
            "note_form": NoteForm(),
            "notes": self.object.notes.select_related("author"),
            "tasks": self.object.tasks.select_related("assigned_to", "created_by"),
            "task_form": TaskForm(
                opportunity=self.object, initial={"assigned_to": self.request.user}
            ),
        }
        context.update(kwargs)
        return super().get_context_data(**context)


class OpportunityCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "oportunitati.add_opportunity"
    model = Opportunity
    form_class = OpportunityForm
    template_name = "oportunitati/form.html"

    def get_initial(self):
        initial = {"owner": self.request.user}
        contact_id = self.request.GET.get("contact")
        if contact_id and contact_id.isdigit():
            initial["contact"] = (
                Contact.objects.visible_to(self.request.user).filter(pk=contact_id).first()
            )
        return initial

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if "owner" not in form.fields:
            form.instance.owner = self.request.user
        response = super().form_valid(form)
        contact = self.object.contact
        if not contact.assignees.exists():
            # Whoever works the opportunity works the contact, until a founder decides otherwise.
            contact.assignees.add(self.object.owner)
        if form.cleaned_data["note"]:
            self.object.notes.create(author=self.request.user, text=form.cleaned_data["note"])
        messages.success(self.request, "Oportunitatea a fost creată.")
        return response


class OpportunityUpdateView(
    PermissionRequiredMixin, VisibleOpportunityMixin, SuccessMessageMixin, UpdateView
):
    permission_required = "oportunitati.change_opportunity"
    form_class = OpportunityForm
    template_name = "oportunitati/form.html"
    success_message = "Modificările au fost salvate."

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}


class OpportunityDeleteView(
    PermissionRequiredMixin, VisibleOpportunityMixin, SuccessMessageMixin, DeleteView
):
    permission_required = "oportunitati.delete_opportunity"
    template_name = "oportunitati/confirm_delete.html"
    success_url = reverse_lazy("oportunitati:list")
    success_message = "Oportunitatea a fost ștearsă."


class OpportunityActionView(PermissionRequiredMixin, View):
    """Base for the POST-only forms on the opportunity page. Invalid input re-renders the
    page with the errors next to the form that caused them."""

    http_method_names = ["post"]

    def get_opportunity(self, pk):
        return get_object_or_404(Opportunity.objects.visible_to(self.request.user), pk=pk)

    def render_page(self, opportunity, **forms):
        page = OpportunityDetailView(request=self.request, kwargs={"pk": opportunity.pk})
        page.object = opportunity
        return page.render_to_response(page.get_context_data(**forms))


class StatusUpdateView(OpportunityActionView):
    permission_required = "oportunitati.change_opportunity"

    def post(self, request, pk):
        opportunity = self.get_opportunity(pk)
        form = StatusForm(request.POST, opportunity=opportunity, user=request.user)
        if not form.is_valid():
            return self.render_page(opportunity, status_form=form)
        camp = form.save()
        message = f"Status schimbat în „{opportunity.get_status_display()}”."
        if camp:
            message += f" Contactul {opportunity.contact.name} a fost adăugat la „{camp.name}”."
        messages.success(request, message)
        return redirect(opportunity)


class NoteCreateView(OpportunityActionView):
    permission_required = "oportunitati.add_note"

    def post(self, request, pk):
        opportunity = self.get_opportunity(pk)
        form = NoteForm(request.POST)
        if not form.is_valid():
            return self.render_page(opportunity, note_form=form)
        form.instance.opportunity = opportunity
        form.instance.author = request.user
        form.save()
        opportunity.touch()
        return redirect(f"{opportunity.get_absolute_url()}#istoric")


class TaskCreateView(OpportunityActionView):
    permission_required = "oportunitati.add_task"

    def post(self, request, pk):
        opportunity = self.get_opportunity(pk)
        form = TaskForm(request.POST, opportunity=opportunity)
        if not form.is_valid():
            return self.render_page(opportunity, task_form=form)
        form.instance.opportunity = opportunity
        form.instance.created_by = request.user
        task = form.save()
        messages.success(request, f"Sarcina a fost atribuită lui {display_name(task.assigned_to)}.")
        return redirect(f"{opportunity.get_absolute_url()}#sarcini")


class TaskToggleView(PermissionRequiredMixin, View):
    permission_required = "oportunitati.change_task"
    http_method_names = ["post"]

    def post(self, request, pk):
        # Whoever the task was given to may tick it, even on someone else's opportunity.
        visible = Opportunity.objects.visible_to(request.user)
        tasks = Task.objects.filter(Q(opportunity__in=visible) | Q(assigned_to=request.user))
        task = get_object_or_404(tasks, pk=pk)
        task.toggle_done()
        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(task.parent_url)
