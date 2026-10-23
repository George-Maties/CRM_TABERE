from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.core.forms import BootstrapFormMixin

from .models import Note, Opportunity, Status, Task


class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()


def team_members():
    """Active users with a role: the people an opportunity or a task can be given to."""
    return (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__isnull=False))
        .distinct()
        .order_by("first_name", "username")
    )


class OpportunityForm(BootstrapFormMixin, forms.ModelForm):
    note = forms.CharField(
        label="Ce ați discutat",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Opțional. Apare ca primă notă în istoric.",
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


class StatusForm(BootstrapFormMixin, forms.Form):
    status = forms.ChoiceField(label="Status", choices=Status.choices)


class NoteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Note
        fields = ["text"]
        labels = {"text": "Notă nouă"}
        widgets = {"text": forms.Textarea(attrs={"rows": 3, "placeholder": "Ce ați discutat…"})}


class TaskForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "assigned_to", "due_date"]
        field_classes = {"assigned_to": UserChoiceField}
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = team_members()
