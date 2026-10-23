from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.accounts.roles import sellers_and_founders
from apps.oportunitati.models import Opportunity

from .forms import AssignForm, ContactForm
from .models import Contact

# Value of the "atribuit" filter that shows the contacts nobody works yet
UNASSIGNED = "nimeni"


def assignable_people():
    """The people listed by the "Atribuie" button, with their roles loaded for the labels."""
    return sellers_and_founders().prefetch_related("groups")


class VisibleContactMixin:
    """Limit every view to the contacts the user may see; others answer 404."""

    def get_queryset(self):
        return Contact.objects.visible_to(self.request.user).prefetch_related("assignees")


class ContactListView(PermissionRequiredMixin, VisibleContactMixin, ListView):
    permission_required = "contacte.view_contact"
    paginate_by = 25
    template_name = "contacte/list.html"

    def get_queryset(self):
        contacts = super().get_queryset()
        self.query = self.request.GET.get("q", "").strip()
        self.kind = self.request.GET.get("tip", "")
        self.assignee = self.request.GET.get("atribuit", "")
        if self.query:
            contacts = contacts.filter(
                Q(name__icontains=self.query)
                | Q(phone__icontains=self.query)
                | Q(email__icontains=self.query)
            )
        if self.kind in Contact.Kind.values:
            contacts = contacts.filter(kind=self.kind)
        if self.assignee == UNASSIGNED:
            contacts = contacts.filter(assignees__isnull=True)
        elif self.assignee.isdigit():
            contacts = contacts.filter(assignees=self.assignee)
        return contacts

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = {
            "query": self.query,
            "kind": self.kind,
            "kinds": Contact.Kind.choices,
            "assignee": self.assignee,
            "unassigned": UNASSIGNED,
            "can_see_all": user.has_perm("contacte.view_all_contacts"),
        }
        if context["can_see_all"]:
            context["team"] = sellers_and_founders()
        if user.has_perm("contacte.assign_contact"):
            context["assignable"] = assignable_people()
        context.update(kwargs)
        return super().get_context_data(**context)


class ContactDetailView(PermissionRequiredMixin, VisibleContactMixin, DetailView):
    permission_required = "contacte.view_contact"
    template_name = "contacte/detail.html"

    def get_context_data(self, **kwargs):
        opportunities = (
            Opportunity.objects.visible_to(self.request.user)
            .filter(contact=self.object)
            .select_related("contact", "owner")
            .with_titles()
        )
        context = {"opportunities": opportunities}
        if self.request.user.has_perm("contacte.assign_contact"):
            context["assignable"] = assignable_people()
        context.update(kwargs)
        return super().get_context_data(**context)


class ContactFormMixin:
    model = Contact
    form_class = ContactForm
    template_name = "contacte/form.html"

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}


class ContactCreateView(PermissionRequiredMixin, ContactFormMixin, SuccessMessageMixin, CreateView):
    permission_required = "contacte.add_contact"
    success_message = "Contactul „%(name)s” a fost adăugat."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        if "assignees" not in form.fields:
            self.object.assignees.add(self.request.user)
        return response


class ContactUpdateView(
    PermissionRequiredMixin, VisibleContactMixin, ContactFormMixin, SuccessMessageMixin, UpdateView
):
    permission_required = "contacte.change_contact"
    success_message = "Modificările au fost salvate."


class ContactDeleteView(
    PermissionRequiredMixin, VisibleContactMixin, SuccessMessageMixin, DeleteView
):
    permission_required = "contacte.delete_contact"
    template_name = "contacte/confirm_delete.html"
    success_url = reverse_lazy("contacte:list")
    success_message = "Contactul a fost șters."


class ContactAssignView(PermissionRequiredMixin, View):
    """Assign the selected contacts, from the list or the contact page, then go back there."""

    permission_required = "contacte.assign_contact"
    http_method_names = ["post"]

    def post(self, request):
        form = AssignForm(request.POST)
        if form.is_valid():
            messages.success(
                request, self.success_text(form.save(), form.cleaned_data["assignees"])
            )
        else:
            for errors in form.errors.values():
                messages.error(request, errors[0])
        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect("contacte:list")

    @staticmethod
    def success_text(count, assignees):
        names = [person.get_full_name() or person.get_username() for person in assignees]
        name = " și ".join([", ".join(names[:-1]), names[-1]]) if len(names) > 1 else names[0]
        if count == 1:
            return f"Contactul a fost atribuit lui {name}."
        # Romanian puts "de" between the number and the noun from 20 up ("20 de contacte").
        de = "de " if count % 100 >= 20 or count % 100 == 0 else ""
        return f"{count} {de}contacte au fost atribuite lui {name}."
