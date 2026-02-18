#!/usr/bin/env bash

# python manage.py makemigrations
# python manage.py migrate
docker compose -f docker-compose-prod.yml exec iriusapp python manage.py collectstatic
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/img iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/css iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ../iriusconfig/static/js iriusapp:/app/static/.
# python manage.py createsuperuser --no-input
