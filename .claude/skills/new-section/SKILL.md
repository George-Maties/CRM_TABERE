---
name: new-section
description: Creează o secțiune nouă în CRM — aplicație Django nouă în apps/, buton în sidebar, folder de template-uri, pagină de bun venit, teste. Folosește-l când utilizatorul cere un modul, o secțiune sau o aplicație nouă în meniu (de ex. „adaugă secțiunea Plăți”).
---

# Secțiune nouă

Respectă `ui-conventions`. Modelul de urmat e `apps/contacte/`: copiază-i structura exact, fără fișiere în plus.

## 1. Stabilește numele

| | Exemplu | Regulă |
|---|---|---|
| pachet / label / namespace URL | `plati` | litere mici, ASCII, fără diacritice |
| eticheta din sidebar | `Plăți` | română cu diacritice |
| iconiță | `bi-credit-card` | din https://icons.getbootstrap.com/ |
| ordine | `40` | citește `order=` din `apps/*/apps.py` și alege poziția (din 10 în 10) |

Dacă utilizatorul nu a spus unde apare secțiunea în meniu, pune-o ultima.

## 2. Aplicația: `apps/<pachet>/`

`__init__.py` (gol)

`apps.py`:
```python
from django.apps import AppConfig

from apps.core.navigation import MenuItem


class PlatiConfig(AppConfig):
    name = "apps.plati"
    label = "plati"
    verbose_name = "Plăți"
    menu_items = (
        MenuItem(label="Plăți", url_name="plati:welcome", icon="bi-credit-card", order=40),
    )
```
Dacă secțiunea e doar pentru anumite roluri, adaugă `permission="plati.view_<model>"`. Butonul se ascunde automat, dar view-ul trebuie protejat și el (vezi `new-page`).

`views.py`:
```python
from django.views.generic import TemplateView


class WelcomeView(TemplateView):
    template_name = "plati/welcome.html"
```

`urls.py`:
```python
from django.urls import path

from .views import WelcomeView

app_name = "plati"

urlpatterns = [
    path("", WelcomeView.as_view(), name="welcome"),
]
```

Nu crea `models.py`, `admin.py` sau `migrations/` până când secțiunea nu are modele.

## 3. Înregistrarea

- `config/settings.py`: adaugă `"apps.<pachet>"` în `INSTALLED_APPS`, după ultima secțiune.
- `config/urls.py`: adaugă `path("<pachet>/", include("apps.<pachet>.urls")),` după ultima secțiune, înainte de blocul `if settings.DEBUG`.

## 4. Template: `templates/<pachet>/welcome.html`

```django
{% extends "layouts/app.html" %}

{% block title %}Plăți{% endblock %}

{% block content %}
  {% include "components/welcome.html" with icon="bi-credit-card" title="Plăți" %}
{% endblock %}
```

## 5. Teste: `apps/core/tests.py`

- Adaugă `"<pachet>:welcome"` în lista `SECTIONS`.
- Adaugă eticheta, la poziția dată de `order`, în lista așteptată din `test_section_renders_with_sidebar`.

## 6. Documentație

În `README.md`, la „Structura”, adaugă rândul `apps/<pachet>/   secțiunea <Etichetă>`.

## 7. Verificare

```bash
source .venv/bin/activate
ruff format . && ruff check .
python manage.py check && python manage.py makemigrations --check --dry-run
pytest && DEBUG=False SECURE_SSL_REDIRECT=False pytest
```
Raportează utilizatorului URL-ul nou (`http://127.0.0.1:8000/<pachet>/`). Nu face commit și nu face push.
