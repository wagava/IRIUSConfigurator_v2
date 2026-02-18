import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

from general.crypt import decrypt_password

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, "storage/.env"))

SECRET_KEY = os.getenv("SECRET_KEY", default="token")

DEBUG = bool(int(os.getenv("DEBUG", default=True)))

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",")

PROD_DB_HOST = os.getenv("PROD_DB_HOST", default="127.0.0.1")
PROD_DB_PORT = os.getenv("PROD_DB_PORT", default="5435")

PLC_IP = os.getenv("PLC_IP", default="192.168.232.32")

POSTGRES_USER = os.getenv("POSTGRES_USER", default="postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", default="postgres")

P_KEY = os.getenv("P_KEY", default="key")


INTERNAL_IPS = [
    "127.0.0.1",
]
# Application definition

INSTALLED_APPS = [
    "general",
    "modules",
    "variables",
    "equipments",
    # 'templatetags',
    "django.contrib.admin",
    "django.contrib.auth",
    "django_bootstrap5",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'django.contrib.sites',
    'rest_framework',
    'rest_framework.authtoken',
    # 'rest_framework_simplejwt.token_blacklist',
    'djoser',
    "django_pam",
    'drf_yasg',
    'accounts',
    'api',
    # 'debug_toolbar',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = "iriusconfig.urls"

TEMPLATES_DIR = BASE_DIR / "templates"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "libraries": {
                # 'formatted_float': 'templatetags.floattags',
                "formatted_tags": "templatetags.formattags",
            },
        },
    },
]

WSGI_APPLICATION = "iriusconfig.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases


# pwd = decrypt_password(POSTGRES_PASSWORD.encode(), P_KEY.encode())

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "USER": POSTGRES_USER,
        "PASSWORD": decrypt_password(POSTGRES_PASSWORD.encode(), P_KEY.encode()),
        "NAME": "IRIUSDB",
        "HOST": "127.0.0.1" if DEBUG else PROD_DB_HOST,
        "PORT": "5432" if DEBUG else PROD_DB_PORT,
        # 'TEST': {
        #     'NAME': 'TESTIRIUSDB'
        # }
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
# if not DEBUG:
BOOTSTRAP5 = {
    'css_url': None,  # Отключаем подключение CSS через CDN
    'javascript_url': None,  # Отключаем подключение JS через CDN
}
# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "ru-RU"
# LANGUAGE_CODE = 'en-EN'
TIME_ZONE = "UTC"

# USE_I18N = True
USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "static/"
if DEBUG:
    STATICFILES_DIRS = [
        BASE_DIR / "static",
        # BASE_DIR / 'static/js',
    ]
else:
    STATIC_ROOT = BASE_DIR / "static"  # os.path.join(BASE_DIR, "static")

CUSTOM_STATIC_ROOT = BASE_DIR / "static"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MEDIA_ROOT = BASE_DIR / "media"

# CSRF_TRUSTED_ORIGINS=['http://192.168.7.55']
if DEBUG:
    CSRF_TRUSTED_ORIGINS = ["http://192.168.222.10"]
# CSRF_TRUSTED_ORIGINS=['*']
else:
    # CSRF_TRUSTED_ORIGINS = ["http://192.168.7.59"]
    CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_HOSTS", default="http://192.168.7.59").split(
        ","
    )

AUTHENTICATION_BACKENDS = [
  'django_pam.auth.backends.PAMBackend',
  'django.contrib.auth.backends.ModelBackend',
]
# PAM_SERVICE = 'login'
PAM_SERVICE = 'sshd'
# # По умолчанию django-pam создает пользователей автоматически, если они прошли аутентификацию через PAM, но еще не существуют в базе данных Django
DJANGO_PAM_CREATE_USER = True  # False - отключить автоматическое создание пользователей

# # использовать конкретную группу Linux для ограничения доступа
DJANGO_PAM_ALLOWED_GROUPS = ['operators']


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django_pam': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}

SITE_ID = 1


REST_FRAMEWORK = {
    
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],

    'DEFAULT_AUTHENTICATION_CLASSES': [
        # 'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # Используем JWT
    ],
    # 'DEFAULT_FILTER_BACKENDS': [
    #     'django_filters.rest_framework.DjangoFilterBackend'
    # ],

    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 5,

    # 'DEFAULT_THROTTLE_CLASSES': [
    #     'rest_framework.throttling.UserRateThrottle',
    #     'rest_framework.throttling.AnonRateThrottle',

    # ],
    # 'DEFAULT_THROTTLE_RATES': {
    #     'user': '100000/minute',
    #     'anon': '100000/minute',
    # },
}

DJOSER = {
    'LOGIN_FIELD': 'username',
    'SEND_ACTIVATION_EMAIL': False,
    'SERIALIZERS': {},
    'TOKEN_MODEL': None,
    # 'LOGIN_FIELD': 'username',
    # 'USER_CREATE_PASSWORD_RETYPE': True,
    # 'SET_PASSWORD_RETYPE': True,
    # 'PASSWORD_RESET_CONFIRM_URL': 'password/reset/confirm/{uid}/{token}',
    # 'USERNAME_RESET_CONFIRM_URL': 'username/reset/confirm/{uid}/{token}',
    # 'ACTIVATION_URL': 'activate/{uid}/{token}',
    # 'SEND_ACTIVATION_EMAIL': False,
    # 'SERIALIZERS': {},
    # 'TOKEN_MODEL': None,  # Отключаем использование токенов Django REST framework
}
APPEND_SLASH = False

SIMPLE_JWT = {
    # Время жизни access-токена (например, 5 минут)
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),

    # Время жизни refresh-токена (например, 1 день)
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),

    # Разрешить использование одного refresh-токена только один раз
    # 'ROTATE_REFRESH_TOKENS': True,

    # Блокировать refresh-токены после выхода пользователя из системы
    # 'BLACKLIST_AFTER_ROTATION': True,

    # Алгоритм подписи токенов
    'ALGORITHM': 'HS256',

    # Ключ для подписи токенов (по умолчанию SECRET_KEY Django)
    # 'SIGNING_KEY': None,

    # Тип токена (по умолчанию "Bearer")
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # удалить cookie-файл сессии при закрытии страницы или всего браузера

SESSION_COOKIE_AGE = 900  # Время жизни сессии в секундах (например, 1800 секунд = 30 минут)
# SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Отключение постоянной сессии — автоматически завершать её при истечении срока
SESSION_SAVE_EVERY_REQUEST = True

# дополнительная защита сессий
SESSION_COOKIE_SECURE = True  # Если ваш проект работает по HTTPS
SESSION_COOKIE_HTTPONLY = True  # Не даёт JavaScript доступ к cookie файлу
# CSRF_USE_SESSIONS = True  # Хранение CSRF токенов в сессии

