from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from apps.oportunitati.models import Opportunity

from .forms import ContactForm
from .models import Contact


class ContactListView(PermissionRequiredMixin, ListView):
    permission_required = "contacte.view_contact"
    model = Contact
    paginate_by = 25
    template_name = "contacte/list.html"

    def get_queryset(self):
        contacts = super().get_queryset()
        self.query = self.request.GET.get("q", "").strip()
        self.kind = self.request.GET.get("tip", "")
        if self.query:
            contacts = contacts.filter(
                Q(name__icontains=self.query)
                | Q(phone__icontains=self.query)
                | Q(email__icontains=self.query)
            )
        if self.kind in Contact.Kind.values:
            contacts = contacts.filter(kind=self.kind)
        return contacts

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            query=self.query, kind=self.kind, kinds=Contact.Kind.choices, **kwargs
        )


class ContactDetailView(PermissionRequiredMixin, DetailView):
    permission_required = "contacte.view_contact"
    model = Contact
    template_name = "contacte/detail.html"

    def get_context_data(self, **kwargs):
        opportunities = (
            Opportunity.objects.visible_to(self.request.user)
            .filter(contact=self.object)
            .select_related("owner")
        )
        return super().get_context_data(opportunities=opportunities, **kwargs)


class ContactCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "contacte.add_contact"
    model = Contact
    form_class = ContactForm
    template_name = "contacte/form.html"
    success_message = "Contactul „%(name)s” a fost adăugat."

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class ContactUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "contacte.change_contact"
    model = Contact
    form_class = ContactForm
    template_name = "contacte/form.html"
    success_message = "Modificările au fost salvate."


class ContactDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    permission_required = "contacte.delete_contact"
    model = Contact
    template_name = "contacte/confirm_delete.html"
    success_url = reverse_lazy("contacte:list")
    success_message = "Contactul a fost șters."
