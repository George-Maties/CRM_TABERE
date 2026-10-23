from django import forms
from django.db import transaction

from apps.accounts.roles import team_members
from apps.core.forms import BootstrapFormMixin, UserChoiceField
from apps.tabere.models import Camp

from .models import OPEN_STATUSES, Note, Opportunity, Status


class OpportunityForm(BootstrapFormMixin, forms.ModelForm):
    note = forms.CharField(
        label="Ce ați discutat",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Obligatoriu dacă statusul nu e „Nou”. Apare ca primă notă în istoric.",
    )

    class Meta:
        model = Opportunity
        fields = ["contact", "title", "status", "owner"]
        field_classes = {"owner": UserChoiceField}
        help_texts = {"title": "De exemplu: Tabăra de vară 2027, 2 copii"}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = team_members()
        # Only roles that see every opportunity may hand one to someone else;
        # anyone else owns what they create, so it never disappears from their list.
        if not user.has_perm("oportunitati.view_all_opportunities"):
            del self.fields["owner"]
        if self.instance.pk:
            # Status and notes change on the opportunity page, where each change is recorded.
            del self.fields["note"]
            del self.fields["status"]
        else:
            # Winning or losing needs a camp or a reason: that happens on the opportunity page.
            self.fields["status"].choices = [(s.value, s.label) for s in OPEN_STATUSES]

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if status and status != Status.NEW and not cleaned.get("note"):
            self.add_error("note", "Scrieți ce ați discutat: statusul nu mai e „Nou”.")
        return cleaned


class StatusForm(BootstrapFormMixin, forms.Form):
    """Change an opportunity's status. Always needs a comment; winning also needs the camp
    the contact joins, either an existing one or a new one created here."""

    status = forms.ChoiceField(label="Status nou", choices=Status.choices)
    camp = forms.ModelChoiceField(
        label="Tabăra",
        queryset=Camp.objects.all(),
        required=False,
        empty_label="Tabără nouă…",
    )
    camp_name = forms.CharField(label="Numele taberei noi", max_length=200, required=False)
    camp_start = forms.DateField(
        label="Începe pe", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    camp_end = forms.DateField(
        label="Se termină pe", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    comment = forms.CharField(
        label="Comentariu",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Obligatoriu. Pentru „Pierdută”, scrieți motivul.",
    )

    def __init__(self, *args, opportunity, user, **kwargs):
        self.opportunity = opportunity
        self.user = user
        kwargs.setdefault("initial", {"status": opportunity.status, "camp": opportunity.camp})
        super().__init__(*args, **kwargs)
        if not user.has_perm("tabere.add_camp"):
            for name in ("camp_name", "camp_start", "camp_end"):
                del self.fields[name]
            self.fields["camp"].empty_label = "Alegeți tabăra…"

    def clean(self):
        cleaned = super().clean()
        status, camp = cleaned.get("status"), cleaned.get("camp")
        if status == Status.WON:
            if camp is None and "camp_name" not in self.fields:
                self.add_error("camp", "Alegeți tabăra în care merge contactul.")
            elif camp is None:
                if not cleaned.get("camp_name"):
                    self.add_error(
                        "camp_name", "Alegeți o tabără existentă sau scrieți numele uneia noi."
                    )
                if not cleaned.get("camp_start"):
                    self.add_error(
                        "camp_start", "Data de început e obligatorie pentru o tabără nouă."
                    )
                start, end = cleaned.get("camp_start"), cleaned.get("camp_end")
                if start and end and end < start:
                    self.add_error("camp_end", "Tabăra nu se poate termina înainte să înceapă.")
            elif status == self.opportunity.status and camp == self.opportunity.camp:
                self.add_error("camp", "Contactul e deja în această tabără.")
        elif status == self.opportunity.status:
            self.add_error("status", "Alegeți un status diferit de cel actual.")
        return cleaned

    @transaction.atomic
    def save(self):
        """Apply the change. Returns the camp the contact joined (None if not won)."""
        data = self.cleaned_data
        camp = data.get("camp")
        if data["status"] == Status.WON and camp is None:
            camp = Camp.objects.create(
                name=data["camp_name"],
                start_date=data["camp_start"],
                end_date=data.get("camp_end"),
                created_by=self.user,
            )
        self.opportunity.change_status(data["status"], self.user, data["comment"], camp=camp)
        return camp if data["status"] == Status.WON else None


class NoteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Note
        fields = ["text"]
        labels = {"text": "Notă nouă"}
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Ce ați discutat…"})}
