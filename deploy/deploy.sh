#!/usr/bin/env bash
# Actualizează aplicația pe server. Se rulează ca utilizatorul crm.
set -euo pipefail

APP_DIR=/srv/crm-tabere/app
VENV=/srv/crm-tabere/venv

cd "$APP_DIR"
git pull --ff-only
"$VENV/bin/pip" install -r requirements.txt
"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput
"$VENV/bin/python" manage.py check --deploy
sudo systemctl reload crm-tabere
