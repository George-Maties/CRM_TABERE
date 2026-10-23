from django import forms

from apps.accounts.roles import team_members
from apps.core.forms import BootstrapFormMixin, UserChoiceField

from .models import Camp, Child, Task


class CampForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Camp
        fields = ["name", "start_date", "end_date", "accommodation", "notes"]
        help_texts = {
            "name": "De exemplu: Tabăra de vară 2027, seria 1",
            "accommodation": "Din lista de cazări. Una nouă o adaugă un fondator, din Cazări.",
        }
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        accommodation = self.fields["accommodation"]
        accommodation.empty_label = "Nealeasă încă"
        accommodation.label_from_instance = lambda place: (
            f"{place} · {place.capacity} locuri" if place.capacity else str(place)
        )

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


class ChildForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Child
        fields = ["name", "age", "city", "medical_notes"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "age": forms.NumberInput(attrs={"min": 1, "max": 30, "inputmode": "numeric"}),
            "city": forms.TextInput(attrs={"autocomplete": "off"}),
            "medical_notes": forms.Textarea(attrs={"rows": 2}),
        }
        error_messages = {
            "age": {
                "min_value": "Vârsta trebuie să fie cel puțin 1.",
                "max_value": "Vârsta nu poate fi mai mare de 30.",
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["age"].required = True
