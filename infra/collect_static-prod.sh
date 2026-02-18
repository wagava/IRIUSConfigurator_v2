#!/usr/bin/env bash

docker compose -f docker-compose-prod.yml exec iriusapp python manage.py collectstatic
docker compose -f docker-compose-prod.yml cp ./static/img iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ./static/css iriusapp:/app/static/.
docker compose -f docker-compose-prod.yml cp ./static/js iriusapp:/app/static/.
