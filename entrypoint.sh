#!/usr/bin/env bash
python manage.py collectstatic --no-input
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/img iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/css iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/js iriusapp:/app/static/.
gunicorn --bind 0.0.0.0:7000 iriusconfig.wsgi