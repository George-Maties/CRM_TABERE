---
name: ui-conventions
description: Regulile de interfață ale CRM Tabere — Bootstrap 5.3 local, layout-uri, componente, formulare, texte în română, responsive, accesibilitate, securitate în template-uri. Citește-l înainte de a scrie sau modifica orice template HTML, CSS, formular sau view care randează o pagină.
---

# Convenții UI — CRM Tabere

## Prioritate față de skill-urile externe

În `.claude/skills/` există și skill-uri de design preluate din comunitate: `frontend-design`, `impeccable`, `ui-ux-pro-max` și `web-design-guidelines` (sursele sunt în `.claude/skills/SOURCES.md`). Folosește-le pentru principii de UX, accesibilitate, ierarhie, texte și critică. Când recomandă ceva ce contrazice acest fișier, **regulile de aici câștigă**: Bootstrap 5.3 local (nu Tailwind sau alte fonturi și biblioteci), layout-urile și componentele existente, text în română cu majusculă doar la început de propoziție. Aplicația e un CRM intern, nu o pagină de prezentare, deci claritatea și consecvența primează în fața efectelor vizuale (fără glassmorphism, gradienți decorativi sau animații de intrare). O schimbare a direcției vizuale (culori, fonturi) se face doar la cererea utilizatorului.

## Stack

- Template-uri Django randate pe server. Fără framework JS și fără pas de build.
- **Bootstrap 5.3.8**, **Bootstrap Icons 1.13.1** și fonturile de brand **Barlow** (text) și **Outfit** (titluri), salvate local în `static/vendor/`. Nu adăuga link-uri CDN. O bibliotecă nouă se descarcă în `static/vendor/<lib>/`, cu versiune fixă.
- CSS propriu în două fișiere: `static/css/theme.css` (culori, fonturi, înlocuirile pentru Bootstrap, tema luminoasă și cea întunecată) și `static/css/app.css` (layout și componente). Folosește întâi clasele utilitare Bootstrap (`d-flex`, `gap-2`, `mb-3`, `text-body-secondary`...). Scrie CSS doar când nu există o utilitară potrivită.
- Culorile vin din token-urile `--app-*` din `theme.css` (`var(--app-primary)`, `var(--app-accent)`, `var(--app-muted)`, `var(--app-border)`...) sau din variabilele Bootstrap mapate pe ele, nu din valori hex scrise direct. Fiecare culoare nouă se definește în **ambele** teme și se verifică la contrast (4,5:1 pentru text, 3:1 pentru iconițe). Culorile de brand vin de pe taberepeterra.com: portocaliul pur `--app-brand` e doar pentru iconițe și accente, iar textul și butoanele folosesc `--app-accent` / `--app-primary`. Dimensiunile layout-ului sunt variabile la începutul `app.css` (`--app-navbar-height`, `--app-sidebar-width`).
- JavaScript: `bootstrap.bundle.min.js`, plus `static/js/preferences.js` (în `<head>`: aplică tema și starea sidebar-ului salvate, înainte de afișare) și `static/js/app.js` (comportamente activate prin atribute: `data-theme-toggle`, `data-sidebar-toggle`, `data-password-toggle`, `form[data-loading-text]`). Un comportament nou se adaugă tot în `app.js`, legat de un atribut `data-*`. Codul specific unei pagini se pune în `{% block extra_js %}`, fără `onclick` inline și fără `<script>` cu cod inline.

## Unde stă fiecare lucru

| Ce | Unde |
|---|---|
| Scheletul HTML (CSS, JS, `<title>`) | `templates/base.html` |
| Pagină cu navbar + sidebar | extinde `templates/layouts/app.html` |
| Pagină fără meniu (login, resetare parolă) | extinde `templates/layouts/auth.html` |
| Navbar (bara de sus a conținutului) | `templates/navbar/` (`navbar.html`, `theme_toggle.html`, `user_menu.html`) |
| Sidebar | `templates/sidebar/` (`sidebar.html`, `brand.html`, `item.html`) |
| Bucăți refolosibile | `templates/components/` (vezi skill-ul `new-component`) |
| Pagini ale unei aplicații | `templates/<app_label>/`, **nu** `apps/<app>/templates/` |
| Butoanele din sidebar | `menu_items` din `apps/<app>/apps.py` (vezi `apps/core/navigation.py`) |

Reguli:
- Nu copia niciodată markup-ul navbar-ului sau al sidebar-ului într-o pagină. Extinde layout-ul.
- O pagină completează `{% block title %}`, cu doar numele paginii (base adaugă ` · {{ brand_name }}`), și `{% block content %}`.
- HTML-ul care apare în două sau mai multe locuri devine componentă în `templates/components/`.

## Context disponibil în orice template

`brand_name`, `home_url`, `sidebar_items` (doar pentru utilizatorii autentificați), `user`, `messages`, `request`. Le furnizează `apps/core/context_processors.py`, deci nu le trimite manual din view.

## Modele vizuale

**Header de pagină:** titlul la stânga, acțiunile la dreapta. Când apare a doua oară, mută-l în `components/page_header.html`.
```django
<div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4">
  <h1 class="h3 mb-0">Contacte</h1>
  <a class="btn btn-primary" href="{% url 'contacte:create' %}">
    <i class="bi bi-plus-lg me-1"></i>Adaugă contact
  </a>
</div>
```

- **Butoane:** cel mult un `btn-primary` pe ecran, pentru acțiunea principală. Celelalte sunt `btn-outline-secondary`, iar `btn-danger` e rezervat acțiunilor distructive.
- **Iconițe:** `<i class="bi bi-..."></i>`, alese de pe https://icons.getbootstrap.com/. Butoanele au iconiță și text. Un buton doar cu iconiță primește obligatoriu `aria-label`.
- **Conținut grupat:** `card` > `card-body`. Un titlu de card se scrie `h2 class="h5"`.
- **Tabele:** `<div class="table-responsive"><table class="table table-hover align-middle">`. Acțiunile pe rând stau în ultima coloană, aliniate la dreapta.
- **Listă goală:** nu lăsa niciodată un tabel gol. Afișează o iconiță mare, o propoziție („Nu există încă niciun contact.”) și butonul de adăugare.
- **Feedback după acțiuni:** în view, `messages.success(request, "Contactul a fost salvat.")`, urmat de redirect (Post/Redirect/Get). Layout-ul afișează mesajul prin `components/messages.html`. Nivelul `error` devine automat `alert-danger`.

## Formulare

- Clasele CSS se pun pe widget-uri în `__init__`-ul formularului, ca în `apps/accounts/forms.py`: `form-control` pentru input și textarea, `form-select` pentru select, `form-check-input` pentru checkbox.
- Un câmp se randează așa. La primul formular real, mută acest bloc în `components/form_field.html`:
  ```django
  <div class="mb-3">
    <label class="form-label" for="{{ field.id_for_label }}">{{ field.label }}</label>
    {{ field }}
    {% for error in field.errors %}<div class="invalid-feedback d-block">{{ error }}</div>{% endfor %}
    {% if field.help_text %}<div class="form-text">{{ field.help_text }}</div>{% endif %}
  </div>
  ```
  Când are erori, câmpul primește clasa `is-invalid` (în formular, după validare, sau în componentă).
- Erorile generale (`form.non_field_errors`) apar într-un `alert alert-danger` deasupra formularului.
- Formularele folosesc mereu `method="post"` și `{% csrf_token %}`. Delogarea și ștergerile se fac **doar prin POST**, niciodată prin link GET.
- Validarea se face pe server. `novalidate` e permis.

## Texte

- Tot textul vizibil e în **română, cu diacritice corecte**: ș și ț cu virgulă (U+0219, U+021B), nu ş/ţ cu sedilă.
- Utilizatorul e abordat formal: „Autentificați-vă”, „Salvați”, „Sunteți sigur?”.
- Numele din cod (variabile, clase, URL names) și comentariile sunt în engleză. Numele de aplicații și URL-urile pot fi în română, fără diacritice (`oportunitati`).
- Datele calendaristice se afișează cu filtrele Django (`{{ d|date:"SHORT_DATE_FORMAT" }}`). Localizarea `ro` le formatează corect.

## Responsive și accesibilitate

- Orice pagină trebuie să funcționeze la 375px lățime. Sidebar-ul devine automat offcanvas sub `lg`. Pentru conținut folosește `row` / `col-md-*`, `flex-wrap`, iar tabelele stau în `table-responsive`.
- Fiecare pagină are un singur `<h1>`. Fiecare input are `<label>`. Culoarea nu e singurul semnal: un badge roșu are și text.
- Elementele interactive sunt `<a>` sau `<button>`, niciodată `<div>` cu click.

## Securitate în template-uri

- Fără `|safe` sau `{% autoescape off %}` pe date introduse de utilizatori.
- Aplicația stochează date despre minori și date medicale. Accesul se verifică în **view** (`PermissionRequiredMixin`, filtrarea queryset-ului). Ascunderea în template nu protejează nimic.
- Nu pune link direct către `MEDIA_URL` pentru documentele încărcate. Ele trec printr-un view care verifică permisiunea, iar în producție nginx le servește prin `X-Accel-Redirect` (vezi `deploy/nginx/crm-tabere.conf`).
- Toate paginile cer login (prin `LoginRequiredMiddleware`). Folosește `@login_not_required` doar pentru pagini cu adevărat publice.

## Verificare după orice schimbare de UI

```bash
source .venv/bin/activate
ruff format . && ruff check .
python manage.py check
pytest && DEBUG=False SECURE_SSL_REDIRECT=False pytest   # local + ca în CI
```
Fiecare pagină nouă are un test care o randează (vezi `new-page`). Nu face commit și nu face push: utilizatorul le face singur.
