# CRM Tabere

CRM pentru o firmă de tabere: Django + PostgreSQL, rulat în producție cu Gunicorn (serviciu systemd) în spatele Nginx.

## Mediul local (WSL / Ubuntu)

### 1. Pachete de sistem (o singură dată)

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip postgresql postgresql-contrib
sudo service postgresql start
```

WSL nu pornește PostgreSQL automat. După fiecare repornire rulați `sudo service postgresql start`, sau activați systemd în `/etc/wsl.conf` (`[boot]` / `systemd=true`).

### 2. Baza de date

```bash
sudo -u postgres createuser --createdb --pwprompt crm_tabere
sudo -u postgres createdb --owner crm_tabere crm_tabere
```

`--createdb` e necesar pentru teste: pytest creează și șterge baza `test_crm_tabere`.

### 3. Aplicația

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env   # completați SECRET_KEY și DB_PASSWORD

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Aplicația pornește la http://localhost:8000/admin/. Verificarea stării este la http://localhost:8000/health/.

### Roluri și date de test

```bash
python manage.py setup_roles          # creează rolurile Fondator și Vânzător (rulat și de deploy.sh)
python manage.py seed_demo            # 10 contacte de test, cu oportunități, note și sarcini
python manage.py seed_demo --reset    # le recreează (șterge doar contactele cu email @example.com)
```

| Rol | Cine | Ce poate |
|---|---|---|
| Dev | superuser | tot, inclusiv administrarea utilizatorilor |
| Fondator | grupul „Fondator” | vede toate contactele și oportunitățile, atribuie contacte vânzătorilor, poate șterge; nu gestionează utilizatori |
| Vânzător | grupul „Vânzător” | vede doar contactele atribuite lui și oportunitățile lui; poate crea tabere și sarcini, dar nu poate edita tabere; nu poate șterge |

Rolurile se atribuie din Administrare → Utilizatori → grupuri. Rolurile noi se creează tot acolo, ca grupuri cu permisiunile bifate. Definițiile rolurilor de bază sunt în `apps/accounts/roles.py`.

### Test de volum

Într-o bază separată (numele trebuie să se termine în `_load`; comanda refuză altfel), cu câțiva utilizatori Fondator / Vânzător creați înainte:

```bash
createdb crm_tabere_load
DB_NAME=crm_tabere_load python manage.py migrate
DB_NAME=crm_tabere_load python manage.py setup_roles
DB_NAME=crm_tabere_load python manage.py seed_load --contacts 10000   # oportunități, note, copii, sarcini
DB_NAME=crm_tabere_load python manage.py runserver
```

Ca să vedeți volumul chiar în baza de lucru: `python manage.py seed_load --here --contacts 5000 --camps 100 --participants 25`. Totul se scoate apoi cu `python manage.py seed_load --remove` (contactele cu email `@volum.example.ro` și taberele marcate „Date de test…”).

Cu `DEBUG=True`, fiecare pagină scrie în consolă câte interogări SQL a făcut și cât a durat („GET /contacte/ 200 · 9 queries, 14 ms SQL, 61 ms total”); peste 30 de interogări apare ca avertisment. Testele din `apps/core/test_queries.py` verifică că listele fac un număr fix de interogări, oricâte rânduri au.

### Comenzi utile

```bash
pytest                    # teste
ruff check . && ruff format .   # lint + formatare
```

## Structura

```
config/                setări, URL-uri, WSGI
apps/accounts/         utilizatorul custom (User), login / logout
apps/core/             lucruri comune: health check, meniul din sidebar
apps/wall/             secțiunea Wall
apps/oportunitati/     secțiunea Oportunități
apps/contacte/         secțiunea Contacte
apps/tabere/           secțiunea Tabere (deocamdată: tabere, participanți, sarcini)
apps/cazari/           secțiunea Cazări (pensiunile folosite de tabere; doar fondatori)
templates/
  base.html            scheletul HTML (CSS, JS)
  layouts/app.html     pagini cu navbar + sidebar
  layouts/auth.html    pagini fără meniu (login)
  navbar/              navbar.html, theme_toggle.html, user_menu.html
  sidebar/             sidebar.html, brand.html, item.html
  components/          bucăți refolosibile (mesaje, logo, inițiale, pagina de bun venit)
  <aplicație>/         template-urile fiecărei aplicații
static/css/theme.css   culori (brand Tabere pe Terra), fonturi, tema luminoasă / întunecată
static/css/app.css     layout și componente (dimensiunile navbar / sidebar sunt variabile CSS)
static/js/             preferences.js (tema, sidebar restrâns), app.js (comportamente data-*)
static/img/            logo.png (de pe taberepeterra.com), contours.svg (fundalul de la login)
static/vendor/         Bootstrap 5.3.8, Bootstrap Icons 1.13.1, fonturile Barlow și Outfit, salvate local
deploy/                systemd, nginx, gunicorn, script de deploy
```

Toată configurația vine din `.env` (vezi `.env.example`). Toate paginile cer autentificare, cu excepția celor marcate cu `@login_not_required`.

### O secțiune nouă în sidebar

1. `python manage.py startapp <nume> apps/<nume>` și adăugați `apps.<nume>` în `INSTALLED_APPS`
2. În `apps/<nume>/apps.py` declarați butonul:
   ```python
   menu_items = (MenuItem(label="Nume", url_name="<nume>:welcome", icon="bi-star", order=40),)
   ```
   `order` stabilește poziția, iar `permission="app.view_model"` ascunde butonul pentru cine nu are dreptul.
3. Adăugați `path("<nume>/", include("apps.<nume>.urls"))` în `config/urls.py`

Iconițele disponibile sunt pe https://icons.getbootstrap.com/.

## Producție (VPS)

Structura pe server:

```
/srv/crm-tabere/app     codul (git clone)
/srv/crm-tabere/venv    mediul Python
/srv/crm-tabere/static  fișiere statice (collectstatic), servite de nginx
/srv/crm-tabere/media   documentele încărcate (private!)
```

### Instalare inițială (o singură dată, ca root)

```bash
apt install -y python3-venv postgresql nginx certbot python3-certbot-nginx git

useradd --system --create-home --home-dir /srv/crm-tabere --shell /bin/bash crm
chmod 755 /srv/crm-tabere
install -d -o crm -g crm /srv/crm-tabere/static
install -d -o crm -g www-data -m 2750 /srv/crm-tabere/media

sudo -u postgres createuser --pwprompt crm_tabere
sudo -u postgres createdb --owner crm_tabere crm_tabere

sudo -u crm git clone https://github.com/George-Maties/CRM_TABERE /srv/crm-tabere/app
sudo -u crm python3 -m venv /srv/crm-tabere/venv
sudo -u crm /srv/crm-tabere/venv/bin/pip install -r /srv/crm-tabere/app/requirements.txt

# .env de producție: DEBUG=False, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, STATIC_ROOT, MEDIA_ROOT
sudo -u crm cp /srv/crm-tabere/app/.env.example /srv/crm-tabere/app/.env
sudo -u crm chmod 600 /srv/crm-tabere/app/.env

cd /srv/crm-tabere/app
sudo -u crm ../venv/bin/python manage.py migrate
sudo -u crm ../venv/bin/python manage.py collectstatic --noinput
sudo -u crm ../venv/bin/python manage.py createsuperuser

cp deploy/systemd/crm-tabere.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now crm-tabere

cp deploy/nginx/crm-tabere.conf /etc/nginx/sites-available/crm-tabere   # editați server_name
ln -s /etc/nginx/sites-available/crm-tabere /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d crm.domeniu.ro

# permite utilizatorului crm să reîncarce serviciul din deploy.sh
echo 'crm ALL=(root) NOPASSWD: /usr/bin/systemctl reload crm-tabere' > /etc/sudoers.d/crm-tabere
```

### Actualizări

```bash
sudo -u crm /srv/crm-tabere/app/deploy/deploy.sh
```

### Loguri

```bash
journalctl -u crm-tabere -f
```

### De făcut înainte de date reale

- backup zilnic al bazei de date (`pg_dump`) și al directorului `media/`, păstrat în afara serverului
