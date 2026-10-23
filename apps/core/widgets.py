from django import forms
from django.urls import reverse
from django.utils.html import format_html


class AutocompleteSelect(forms.Widget):
    """Choose one of thousands by typing, where a <select> would be too long to load: a search
    box that asks `url_name` for matches (JSON {"results": [{"id", "label", "detail"}]}) and
    keeps the chosen id in a hidden input. Behaviour: [data-autocomplete] in app.js.

    `label(value)` gives the text shown for the chosen id; the form sets it, so it only finds
    what the user may see."""

    def __init__(self, url_name, placeholder="", attrs=None):
        super().__init__(attrs)
        self.url_name = url_name
        self.placeholder = placeholder
        self.label = str

    def id_for_label(self, id_):
        # The <label> points at the search box, not at the hidden input.
        return f"{id_}_cauta" if id_ else id_

    def value_from_datadict(self, data, files, name):
        return data.get(name)

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        id_ = attrs.pop("id", f"id_{name}")
        css = attrs.pop("class", "form-control")
        chosen = "" if value in (None, "") else str(value)
        return format_html(
            '<div class="autocomplete" data-autocomplete="{url}">'
            '<input type="hidden" name="{name}" id="{id}" value="{value}" data-autocomplete-value>'
            '<input type="search" class="{css}" id="{id}_cauta" value="{text}" placeholder="{hint}"'
            ' role="combobox" aria-autocomplete="list" aria-expanded="false"'
            ' aria-controls="{id}_lista" autocomplete="off" spellcheck="false"'
            " data-autocomplete-input>"
            '<ul class="autocomplete-list" id="{id}_lista" role="listbox" hidden></ul>'
            "</div>",
            url=reverse(self.url_name),
            name=name,
            id=id_,
            value=chosen,
            css=css,
            text=self.label(chosen) if chosen else "",
            hint=self.placeholder,
        )
