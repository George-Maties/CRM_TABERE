from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.contacte.models import Contact

from .forms import NoteForm, OpportunityForm, StatusForm
from .models import Opportunity, Status


class VisibleOpportunityMixin:
    """Limit every view to the opportunities the user may see; others answer 404."""

    def get_queryset(self):
        return Opportunity.objects.visible_to(self.request.user).select_related("contact", "owner")


class OpportunityListView(PermissionRequiredMixin, VisibleOpportunityMixin, ListView):
    permission_required = "oportunitati.view_opportunity"
    paginate_by = 25
    template_name = "oportunitati/list.html"

    def get_queryset(self):
        opportunities = super().get_queryset()
        self.query = self.request.GET.get("q", "").strip()
        self.mine = self.request.GET.get("ale_mele") == "1"
        self.status = self.request.GET.get("status", "")
        if self.query:
            opportunities = opportunities.filter(
                Q(title__icontains=self.query) | Q(contact__name__icontains=self.query)
            )
        if self.mine:
            opportunities = opportunities.filter(owner=self.request.user)
        # Counts per status ignore the status filter itself, so every tab shows its number.
        self.counts = dict(
            opportunities.order_by()
            .values_list("status")
            .annotate(total=Count("id", distinct=True))
        )
        if self.status in Status.values:
            opportunities = opportunities.filter(status=self.status)
        return opportunities

    def get_context_data(self, **kwargs):
        status_tabs = [
            {"value": value, "label": label, "count": self.counts.get(value, 0)}
            for value, label in Status.choices
        ]
        return super().get_context_data(
            query=self.query,
            mine=self.mine,
            status=self.status,
            status_tabs=status_tabs,
            total=sum(self.counts.values()),
            can_see_all=self.request.user.has_perm("oportunitati.view_all_opportunities"),
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
            initial["contact"] = Contact.objects.filter(pk=contact_id).first()
        return initial

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if "owner" not in form.fields:
            form.instance.owner = self.request.user
        response = super().form_valid(form)
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
