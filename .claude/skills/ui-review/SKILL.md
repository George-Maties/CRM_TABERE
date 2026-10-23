---
name: ui-review
description: Verifică template-urile și CSS-ul CRM Tabere față de regulile din ui-conventions — layout, componente duplicate, texte și diacritice, responsive, accesibilitate, securitate. Folosește-l când utilizatorul cere o verificare sau un review al interfeței, sau după o modificare mare de UI.
---

# Review UI

Regulile de referință sunt în `ui-conventions`. Dacă utilizatorul nu a dat fișiere anume, verifică ce s-a schimbat (`git status`, `git diff`, plus fișierele noi netrackuite) sau tot folderul `templates/`.

## Ce verifici

**Structură**
- Fiecare pagină extinde `layouts/app.html` sau `layouts/auth.html`. Nicio pagină nu conține markup copiat din navbar sau sidebar.
- `{% block title %}` e completat pe fiecare pagină.
- Template-urile stau în `templates/<app_label>/`, nu în `apps/<app>/templates/`.
- Un HTML repetat în 2 sau mai multe locuri trebuie mutat într-o componentă.

**Stil**
- Fără `style="..."` inline. Fără culori hex în `app.css` acolo unde există o variabilă `--bs-*`.
- Fără link-uri CDN și fără `<script>` cu cod inline.
- Cel mult un `btn-primary` pe ecran, iar `btn-danger` apare doar la acțiuni distructive.

**Texte**
- Tot textul vizibil e în română. Caută ş/ţ cu sedilă, care sunt greșite:
  ```bash
  grep -rnP '[\x{015F}\x{0163}\x{015E}\x{0162}]' templates apps
  ```
- Adresarea e formală și consecventă.

**Responsive și accesibilitate**
- Tabelele sunt în `table-responsive`. Rândurile de butoane și header-ele au `flex-wrap`.
- Un singur `<h1>` pe pagină. Fiecare input are `<label for>`.
- Butoanele doar cu iconiță au `aria-label`. Nu se folosește `<div>` sau `<span>` cu click.

**Securitate**
- Fără `|safe` sau `autoescape off` pe date de la utilizatori.
- Formularele POST au `{% csrf_token %}`. Delogarea și ștergerea se fac doar prin POST.
- Niciun link direct către `MEDIA_URL`. Datele sensibile sunt protejate în view, nu doar ascunse în template.
- `@login_not_required` apare doar pe pagini cu adevărat publice.

**Teste**
- Fiecare pagină nouă are un test care o randează și unul pentru acces neautentificat (sau fără permisiune).

## Cum raportezi

Prezintă problemele grupate după gravitate: întâi **securitate**, apoi **funcțional sau accesibilitate**, apoi **stil și consecvență**. Fiecare problemă are fișier și linie (`templates/x.html:12`), problema într-o frază și remedierea propusă. Dacă nu găsești nimic într-o categorie, spune asta într-un rând.

Nu modifica fișierele în timpul review-ului. Întreabă utilizatorul dacă vrea să aplici remedierile.
