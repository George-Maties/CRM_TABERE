from django import forms

from apps.accounts.roles import team_members
from apps.contacte.models import Contact
from apps.core.forms import BootstrapFormMixin, UserChoiceField
from apps.tabere.models import Camp

from .models import Note, Opportunity, Status


class OpportunityForm(BootstrapFormMixin, forms.ModelForm):
    note = forms.CharField(
        label="Ce ați discutat",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=(
            "De exemplu: tabăra de vară, 2 copii (9 și 11 ani). Apare ca primă notă în istoric."
        ),
    )

    class Meta:
        model = Opportunity
        fields = ["contact", "owner"]
        field_classes = {"owner": UserChoiceField}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact"].queryset = Contact.objects.visible_to(user)
        self.fields["owner"].queryset = team_members()
        # Only roles that see every opportunity may hand one to someone else;
        # anyone else owns what they create, so it never disappears from their list.
        # A lost opportunity has nobody; reopening it gives it an owner again.
        if (
            not user.has_perm("oportunitati.view_all_opportunities")
            or self.instance.status == Status.LOST
        ):
            del self.fields["owner"]
        if self.instance.pk:
            # Notes are added on the opportunity page, with the rest of the history.
            del self.fields["note"]

    def save(self, commit=True):
        if "contact" in self.changed_data and self.instance.pk:
            # Moved to another contact: it takes the next number there.
            self.instance.number = None
        return super().save(commit)


class StatusForm(BootstrapFormMixin, forms.Form):
    """Change an opportunity's status. Winning needs the camp the contact joins, which must
    already exist; losing needs the reason, saved as a note."""

    status = forms.ChoiceField(label="Status nou", choices=Status.choices)
    camp = forms.ModelChoiceField(
        label="Tabăra",
        queryset=Camp.objects.all(),
        required=False,
        empty_label="Alegeți tabăra…",
    )
    reason = forms.CharField(
        label="Motivul pierderii",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Apare ca notă în istoric.",
    )

    def __init__(self, *args, opportunity, user, **kwargs):
        self.opportunity = opportunity
        self.user = user
        kwargs.setdefault("initial", {"status": opportunity.status, "camp": opportunity.camp})
        super().__init__(*args, **kwargs)
        if not self.fields["camp"].queryset.exists():
            self.fields[
                "camp"
            ].help_text = "Nu există încă nicio tabără. Adăugați-o întâi din secțiunea Tabere."

    def clean(self):
        cleaned = super().clean()
        status, camp = cleaned.get("status"), cleaned.get("camp")
        if status == Status.WON:
            if camp is None:
                self.add_error("camp", "Alegeți tabăra în care merge contactul.")
            elif status == self.opportunity.status and camp == self.opportunity.camp:
                self.add_error("camp", "Contactul e deja în această tabără.")
        elif status == self.opportunity.status:
            self.add_error("status", "Alegeți un status diferit de cel actual.")
        elif status == Status.LOST and not cleaned.get("reason", "").strip():
            self.add_error("reason", "Scrieți motivul pentru care oportunitatea e pierdută.")
        return cleaned

    def save(self):
        """Apply the change. Returns the camp the contact joined (None if not won)."""
        data = self.cleaned_data
        camp = data["camp"] if data["status"] == Status.WON else None
        # The reason belongs only to "lost"; text typed and then hidden is not kept.
        reason = data["reason"].strip() if data["status"] == Status.LOST else ""
        self.opportunity.change_status(data["status"], self.user, reason, camp=camp)
        return camp


class NoteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Note
        fields = ["text"]
        labels = {"text": "Notă nouă"}
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Ce ați discutat…"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only status changes are saved without text.
        self.fields["text"].required = True
