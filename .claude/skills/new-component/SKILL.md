---
name: new-component
description: Creează o componentă de interfață refolosibilă în templates/components/ — header de pagină, câmp de formular, stare goală, card de statistică, badge de status, buton de confirmare etc. Folosește-l când același HTML apare în mai multe locuri sau când utilizatorul cere o componentă UI.
---

# Componentă nouă

Respectă `ui-conventions`. Componentele existente: `templates/components/` (`logo.html`, `messages.html`, `welcome.html`). Verifică întâi să nu existe deja una potrivită.

## 1. Fișierul: `templates/components/<nume>.html`

- Numele fișierului e în engleză, `snake_case`: `page_header.html`, `form_field.html`, `empty_state.html`.
- Prima parte a fișierului e un comentariu cu utilizarea și parametrii:
  ```django
  {% comment %}
    Usage: {% include "components/empty_state.html" with icon="bi-people" text="Nu există încă niciun contact." action_url=create_url action_label="Adaugă contact" %}
    Required: icon, text
    Optional: action_url, action_label (the button appears only if both are given)
  {% endcomment %}
  <div class="text-center py-5 text-body-secondary">
    <i class="bi {{ icon }} empty-state-icon"></i>
    <p class="mt-3">{{ text }}</p>
    {% if action_url and action_label %}
      <a class="btn btn-primary" href="{{ action_url }}">{{ action_label }}</a>
    {% endif %}
  </div>
  ```
- Valorile implicite se dau cu `{{ param|default:"..." }}`.
- Componenta nu depinde de variabile ale paginii. Primește tot prin `with`. Dacă poate fi folosită oriunde, recomandă `{% include ... with ... only %}`.
- Markup-ul folosește clase Bootstrap. CSS-ul propriu, dacă e nevoie, merge în `static/css/app.css`, sub comentariul `/* Component: <nume> */`, cu clase prefixate cu numele componentei (`.empty-state-icon`).

## 2. Când e nevoie de logică: inclusion tag

Dacă componenta trebuie să calculeze ceva (de exemplu un badge care alege culoarea după status), nu pune logica în template. Creează un tag:

- `apps/core/templatetags/__init__.py` (gol) și `apps/core/templatetags/ui.py`:
  ```python
  from django import template

  register = template.Library()

  STATUS_COLORS = {"nou": "secondary", "confirmat": "success", "anulat": "danger"}


  @register.inclusion_tag("components/status_badge.html")
  def status_badge(status, label):
      return {"color": STATUS_COLORS.get(status, "secondary"), "label": label}
  ```
- Folosire: `{% load ui %}` ... `{% status_badge obj.status obj.get_status_display %}`

## 3. Înlocuiește duplicatele

Caută în `templates/` markup-ul pe care îl înlocuiește componenta și folosește componenta peste tot unde apare. Altfel componenta nu-și are rostul.

## 4. Test: `apps/core/tests.py`

```python
from django.template.loader import render_to_string


def test_empty_state_hides_button_without_action():
    html = render_to_string("components/empty_state.html", {"icon": "bi-people", "text": "Gol"})
    assert "Gol" in html
    assert "btn" not in html
```
Testează ramurile din componentă: parametrii opționali și valorile implicite.

## 5. Verificare

```bash
source .venv/bin/activate
ruff format . && ruff check .
pytest && DEBUG=False SECURE_SSL_REDIRECT=False pytest
```
Spune-i utilizatorului cum se folosește componenta (linia `Usage`). Nu face commit și nu face push.
