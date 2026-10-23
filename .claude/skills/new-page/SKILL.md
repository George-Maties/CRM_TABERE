---
name: new-page
description: Adaugă o pagină nouă într-o secțiune existentă a CRM-ului — view, URL, template care extinde layout-ul, permisiuni, teste. Folosește-l pentru liste, detalii, formulare de adăugare/editare, confirmări de ștergere sau orice ecran nou în Wall, Oportunități, Contacte etc.
---

# Pagină nouă într-o secțiune

Respectă `ui-conventions`. Dacă secțiunea nu există încă, folosește întâi `new-section`.

## 1. View: `apps/<app>/views.py`

- Folosește view-uri generice, bazate pe clase: `TemplateView`, `ListView`, `DetailView`, `CreateView`, `UpdateView`, `DeleteView`.
- Login-ul e deja impus de `LoginRequiredMiddleware`, deci nu adăuga `LoginRequiredMixin`.
- Dacă pagina e doar pentru anumite roluri, adaugă `PermissionRequiredMixin` cu `permission_required = "<app>.<perm>_<model>"`. Pentru datele sensibile (medicale, acte, plăți), filtrează și queryset-ul în `get_queryset()`.
- `ListView` primește `paginate_by = 25`.
- În formulare: la succes, `messages.success(self.request, "...")` în `form_valid`, apoi redirect prin `success_url = reverse_lazy("<app>:<pagina>")`.

## 2. URL: `apps/<app>/urls.py`

```python
path("<int:pk>/", ContactDetailView.as_view(), name="detail"),
```
Numele sunt în engleză și scurte: `list`, `detail`, `create`, `update`, `delete`. Butonul din sidebar rămâne activ automat pe toate paginile secțiunii, pentru că URL-urile încep cu prefixul ei.

## 3. Template: `templates/<app>/<nume>.html`

Numele fișierelor: `list.html`, `detail.html`, `form.html` (comun pentru create și update), `confirm_delete.html`.

```django
{% extends "layouts/app.html" %}

{% block title %}Contacte{% endblock %}

{% block content %}
  <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4">
    <h1 class="h3 mb-0">Contacte</h1>
    <a class="btn btn-primary" href="{% url 'contacte:create' %}">
      <i class="bi bi-plus-lg me-1"></i>Adaugă contact
    </a>
  </div>

  {% if object_list %}
    <div class="table-responsive">
      <table class="table table-hover align-middle">
        ...
      </table>
    </div>
  {% else %}
    {# stare goală: iconiță + propoziție + buton de adăugare #}
  {% endif %}
{% endblock %}
```

- Folosește componentele existente din `templates/components/`. Înainte să scrii markup, verifică ce există deja.
- Un header, câmp de formular sau stare goală care apare a doua oară devine componentă (vezi `new-component`).
- Pentru formulare, urmează secțiunea „Formulare” din `ui-conventions`.
- Ștergerea se face pe o pagină de confirmare, cu formular POST și buton `btn-danger`, niciodată printr-un link direct.

## 4. Teste: `apps/<app>/tests.py`

Cel puțin:
```python
@pytest.mark.django_db
def test_list_renders(admin_client):
    response = admin_client.get(reverse("contacte:list"))
    assert response.status_code == 200


def test_list_requires_login(client):
    url = reverse("contacte:list")
    response = client.get(url)
    assert response.url == f"{reverse('accounts:login')}?next={url}"
```
Plus, după caz:
- pagină cu permisiune: un utilizator fără permisiune primește `403`;
- formular: un POST valid creează sau modifică și face redirect, iar un POST invalid reafișează erorile (`200` și `form.errors`);
- listă: rândurile se văd, iar starea goală apare când nu există date.

## 5. Verificare

```bash
source .venv/bin/activate
ruff format . && ruff check .
python manage.py check && python manage.py makemigrations --check --dry-run
pytest && DEBUG=False SECURE_SSL_REDIRECT=False pytest
```
Raportează URL-ul paginii. Dacă a fost posibil, verifică pagina și în `runserver`. Nu face commit și nu face push.
