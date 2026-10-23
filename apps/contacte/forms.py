from django import forms

from apps.accounts.roles import sellers_and_founders
from apps.core.forms import BootstrapFormMixin, UserMultipleChoiceField

from .models import Contact


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "kind", "phone", "email", "assignees", "notes"]
        field_classes = {"assignees": UserMultipleChoiceField}
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "assignees": forms.CheckboxSelectMultiple,
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        # Who works a contact is decided by roles that assign; anyone else keeps what they add,
        # so it never disappears from their list.
        if user.has_perm("contacte.assign_contact"):
            self.fields["assignees"].queryset = sellers_and_founders()
            self.fields["assignees"].help_text = "Nebifat niciunul, contactul rămâne neatribuit."
        else:
            del self.fields["assignees"]


class AssignForm(forms.Form):
    """Give one or more contacts to one or more people (from the list or the contact page)."""

    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        error_messages={"required": "Selectați cel puțin un contact."},
    )
    # Required, so a forgotten choice never unassigns; that is done from the contact form.
    assignees = UserMultipleChoiceField(
        queryset=sellers_and_founders(),
        error_messages={"required": "Alegeți cui atribuiți contactele."},
    )

    def save(self):
        data = self.cleaned_data
        return data["contacts"].assign(data["assignees"])
