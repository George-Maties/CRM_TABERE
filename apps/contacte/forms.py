from django import forms

from apps.core.forms import BootstrapFormMixin

from .models import Contact


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "kind", "phone", "email", "notes"]
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
