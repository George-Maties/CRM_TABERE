from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AccommodationForm
from .models import Accommodation


class AccommodationListView(PermissionRequiredMixin, ListView):
    permission_required = "cazari.view_accommodation"
    model = Accommodation
    template_name = "cazari/list.html"

    def get_queryset(self):
        return super().get_queryset().annotate(camp_count=Count("camps"))


class AccommodationFormMixin(SuccessMessageMixin):
    model = Accommodation
    form_class = AccommodationForm
    template_name = "cazari/form.html"
    success_url = reverse_lazy("cazari:list")


class AccommodationCreateView(PermissionRequiredMixin, AccommodationFormMixin, CreateView):
    permission_required = "cazari.add_accommodation"
    success_message = "Cazarea „%(name)s” a fost adăugată."


class AccommodationUpdateView(PermissionRequiredMixin, AccommodationFormMixin, UpdateView):
    permission_required = "cazari.change_accommodation"
    success_message = "Modificările au fost salvate."


class AccommodationDeleteView(PermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    permission_required = "cazari.delete_accommodation"
    model = Accommodation
    template_name = "cazari/confirm_delete.html"
    success_url = reverse_lazy("cazari:list")
    success_message = "Cazarea a fost ștearsă."

    def form_valid(self, form):
        # Camps point at their accommodation; it goes only once no camp uses it.
        if self.object.camps.exists():
            messages.error(self.request, "Cazarea e folosită de tabere și nu poate fi ștearsă.")
            return redirect(self.object)
        return super().form_valid(form)
