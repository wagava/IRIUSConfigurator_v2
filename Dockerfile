FROM python:3.9
# FROM python:3.9.20-bullseye

WORKDIR /app

# ENV DJANGO_SUPERUSER_USERNAME iriusadmin
# ENV DJANGO_SUPERUSER_PASSWORD qwer123!
# ENV DJANGO_SUPERUSER_EMAIL adminr@domain.com
ENV DJANGO_SETTINGS_MODULE 'iriusconfig.settings'

COPY ./requirements.txt .

RUN apt-get update && \
    apt-get install -y chrony libkrb5-dev krb5-locales libnss-sss libpam-sss sssd sssd-tools && \
    rm -rf /var/lib/apt/lists/*

RUN  pip install --upgrade pip \
     && pip install gunicorn==20.1.0 \
     && pip install -r requirements.txt --no-cache-dir \
     && mkdir -p /app/static/

COPY ./iriusconfig .
COPY ./iriusconfig/static/css ./static
COPY ./iriusconfig/static/img ./static
COPY ./iriusconfig/static/js ./static


# RUN  python manage.py collectstatic --no-input \
#      && python manage.py createsuperuser --no-input
# RUN  python manage.py createsuperuser --no-input

# EXPOSE 7000

CMD ["gunicorn", "--bind", "0.0.0.0:7000", "iriusconfig.wsgi"]
# ENTRYPOINT ["sh", "entrypoint.sh"]