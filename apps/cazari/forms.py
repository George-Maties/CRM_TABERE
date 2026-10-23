from django import forms

from apps.core.forms import BootstrapFormMixin

from .models import Accommodation


class AccommodationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Accommodation
        fields = ["name", "city", "capacity", "contact_name", "phone"]
        help_texts = {"name": "De exemplu: Pensiunea Bradul"}
        widgets = {
            "capacity": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "off"}),
        }
        error_messages = {"capacity": {"min_value": "Cazarea trebuie să aibă cel puțin un loc."}}
