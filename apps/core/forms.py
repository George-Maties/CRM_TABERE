from django import forms


class UserChoiceField(forms.ModelChoiceField):
    """User select that shows names ("Ana Popescu") instead of usernames."""

    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()


class UserMultipleChoiceField(forms.ModelMultipleChoiceField):
    """Several users, shown by name, like UserChoiceField."""

    def label_from_instance(self, obj):
        return obj.get_full_name() or obj.get_username()


class BootstrapFormMixin:
    """Adds Bootstrap classes to every widget, so templates can render fields as they are."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                css_class = "form-check-input"
            elif isinstance(widget, forms.Select):
                css_class = "form-select"
            else:
                css_class = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css_class}".strip()
