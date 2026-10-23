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

### Comenzi utile

```bash
pytest                    # teste
ruff check . && ruff format .   # lint + formatare
```

## Structura

```
config/          setări, URL-uri, WSGI
apps/accounts/   utilizatorul custom (User)
apps/core/       lucruri comune (health check)
templates/       șabloane HTML
static/          CSS / JS / imagini
deploy/          systemd, nginx, gunicorn, script de deploy
```

Toată configurația vine din `.env` (vezi `.env.example`).

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
