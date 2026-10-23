from django import forms

from apps.accounts.roles import team_members
from apps.core.forms import BootstrapFormMixin, UserChoiceField

from .models import Camp, Task


class CampForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Camp
        fields = ["name", "start_date", "end_date", "location", "notes"]
        help_texts = {"name": "De exemplu: Tabăra de vară 2027, seria 1"}
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "Tabăra nu se poate termina înainte să înceapă.")
        return cleaned


class TaskForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "assigned_to", "due_date"]
        field_classes = {"assigned_to": UserChoiceField}
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = team_members()
