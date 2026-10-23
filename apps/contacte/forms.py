from django import forms

from apps.accounts.roles import team_members
from apps.core.forms import BootstrapFormMixin, UserChoiceField

from .models import Contact

UNASSIGNED_LABEL = "Nimeni (neatribuit)"


class ContactForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Contact
        fields = ["name", "kind", "phone", "email", "assigned_to", "notes"]
        field_classes = {"assigned_to": UserChoiceField}
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "autocomplete": "off"}),
            "email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        # Who works a contact is decided by roles that assign; anyone else keeps what they add,
        # so it never disappears from their list.
        if user.has_perm("contacte.assign_contact"):
            self.fields["assigned_to"].queryset = team_members()
            self.fields["assigned_to"].empty_label = UNASSIGNED_LABEL
            if self.instance.pk:
                self.fields[
                    "assigned_to"
                ].help_text = "Oportunitățile deschise trec și ele la noul responsabil."
        else:
            del self.fields["assigned_to"]


class AssignForm(BootstrapFormMixin, forms.Form):
    """Give one or more contacts to a team member (from the list or the contact page)."""

    contacts = forms.ModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        error_messages={"required": "Selectați cel puțin un contact."},
    )
    # Required, so a forgotten choice never unassigns; that is done from the contact form.
    assigned_to = UserChoiceField(
        label="Atribuie lui",
        queryset=team_members(),
        empty_label="Alegeți persoana…",
        error_messages={"required": "Alegeți cui atribuiți contactele."},
    )
    move_opportunities = forms.BooleanField(
        label="Mută și oportunitățile deschise la noul responsabil",
        required=False,
        initial=True,
    )

    def save(self):
        data = self.cleaned_data
        return data["contacts"].assign(
            data["assigned_to"], move_open_opportunities=data["move_opportunities"]
        )
