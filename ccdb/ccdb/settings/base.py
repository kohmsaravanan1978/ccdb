import os

from celery import signals
from celery.schedules import crontab
from django.utils.translation import gettext_lazy as _

SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SETTINGS_DIR))
MEDIA_ROOT = os.path.join(os.environ.get("SHARED_STORE", "/tmp"), "media/")
MEDIA_URL = "/media/"

OWN_INSTALLED_APPS = [
    "api.apps.ApiConfig",
    "main",
    "globalways",
    "contracting",
]


LOCALE_PATHS = (os.path.join(BASE_DIR, "ccdb", "locale"),)

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# redirect http to https (if not already done by the reverse proxy)
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^globalways/health-check$"]
# set the secure flag on cookies to prevent them from being sent by clients over plain http
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# enable HSTS
SECURE_HSTS_SECONDS = 12 * 30 * 24 * 3600

DEBUG = True
TEST_MODE = os.environ.get("TEST_MODE") in ("1", 1)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY and DEBUG:
    path = ".secret_key"
    try:
        with open(path, "r") as f:
            SECRET_KEY = f.read().strip()
    except FileNotFoundError:
        from django.utils.crypto import get_random_string

        SECRET_KEY = get_random_string(50)
        with open(path, "w") as f:
            f.write(SECRET_KEY)

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.BrowsableAPIRenderer",
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": 1,
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "SEARCH_PARAM": "q",
    "ORDERING_PARAM": "o",
    "VERSIONING_PARAM": "v",
    "DATETIME_FORMAT": "iso-8601",
    "PAGE_SIZE": 100,
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.memcached.PyLibMCCache",
        "LOCATION": os.environ.get("MEMCACHED_LOCATION", ""),
    },
}

CELERY_BROKER_URL = f"amqp://guest:guest@{os.environ.get('CELERY_BROKER_HOST')}:5672//"
CELERY_RESULT_BACKEND = f"cache+memcached://{CACHES['default']['LOCATION']}/"

CELERYD_HIJACK_ROOT_LOGGER = False

CELERY_BEAT_SCHEDULE = {}

CELERY_TASK_DEFAULT_QUEUE = "ccdb-default"
CELERY_TASK_ROUTES = {}

CELERY_timezone = "Europe/Berlin"
CELERY_ENABLE_UTC = False


DEBUG_ALLOWED_CELERY_TASKS = [
    # celery internal needed tasks if running celery
    "celery.chord_unlock",
    "celery.group",
    "celery.backend_cleanup",
    "celery.map",
    "celery.chain",
    "celery.accumulate",
    "celery.starmap",
    "celery.chord",
    "celery.chunks",
    "celery.ping",
    # tasks to run in celery. otherwise there are mocked aways
    "contracting.tasks.task_import_contracts",
    "contracting.tasks.task_import_products_from_contract_posts",
    "contracting.tasks.task_update_contract_status",
    "contracting.tasks.run_invoicing",
    "contracting.tasks.easybill_sync_invoices",
    "contracting.tasks.create_test_log",
    "main.tasks.send_queue_task",
]

CELERY_BEAT_SCHEDULE = {
    "task_run_invoicing": {
        "task": "contracting.tasks.run_invoicing",
        "schedule": crontab(minute="0", hour="3"),
    },
    "task_easybill_sync_invoices": {
        "task": "contracting.tasks.easybill_sync_invoices",
        "schedule": crontab(minute="0", hour="4"),
    },
    # "task_update_contract_status": {
    #     "task": "contracting.tasks.task_update_contract_status",
    #     "schedule": crontab(minute="0", hour="0"),
    # },
}

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "rest_framework.authtoken",
    "django_extensions",
    "django_filters",
    "drf_yasg",
    "celery.contrib.testing",
    "celery.contrib.testing.tasks",
    "import_export",
    "simple_history",
    "jsoneditor",
] + OWN_INSTALLED_APPS

AUTHENTICATION_BACKENDS = ("django.contrib.auth.backends.ModelBackend",)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "crum.CurrentRequestUserMiddleware",
    "csp.middleware.CSPMiddleware",
]

ROOT_URLCONF = "ccdb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": True,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "ccdb.wsgi.application"


DATA_UPLOAD_MAX_NUMBER_FIELDS = None
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", ""),
        "USER": os.environ.get("POSTGRES_USER", ""),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", ""),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 120,
    },
    # The configuration is not part of the deployment
}

# Password validation
# https://docs.djangoproject.com/en/1.10/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/1.10/topics/i18n/
TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ("de", _("German")),
    ("en", _("English")),
]

LANGUAGE_CODE = "en-us"
LANGUAGE_DEFAULT = "de"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.10/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")


@signals.setup_logging.connect
def setup_logging(**kwargs):
    """Setup logging."""
    pass


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.environ.get(
                "LOGGING_DIRECTORY",
                "/tmp",
            )
            + "/django.log",
            "formatter": "normal",
            "backupCount": 40,
            "when": "midnight",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "normal",
        },
    },
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(pathname)s:%(lineno)d %(funcName)s %(process)d %(thread)d %(message)s"
        },
        "normal": {"format": "%(asctime)s %(levelname)s %(message)s"},
        "default": {"format": "[%(name)s: %(levelname)s] %(message)s"},
    },
    "loggers": {
        "": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
        },
        "celery": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["file", "console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file", "console"],
            "level": "ERROR",
            "propagate": True,
        },
        "urllib3": {"level": "WARNING"},
        "easybill.client": {"level": "INFO"},
    },
}

LOGIN_REDIRECT_URL = "/accounts/sso-redirect/"
LOGIN_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/"

ALLOWED_HOSTS = ["*"]

TOKEN_AUTH_MAP = {}
TOKEN_AUTH_IP_HTTP_HEADER_FIELD = "HTTP_X_FORWARDED_FOR"

CSP_DEFAULT_SRC = ["'self'"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
CSP_SCRIPT_SRC = ["'self'"]
CSP_INCLUDE_NONCE_IN = ["script-src"]

CUSTOMER_API_ENDPOINT = "https://rzm.intern.dc1.com/api/v1/crm/customer/"

APIS = dict(
    gnom=dict(
        base=os.environ.get("RZM_API_URL", None),
        token=os.environ.get("RZM_API_TOKEN", None),
    )
)

EASYBILL_API_KEY = os.environ.get("EASYBILL_API_KEY", None)
EASYBILL_PDF_TEMPLATE = os.environ.get("EASYBILL_PDF_TEMPLATE", None)
GLOBALWAYS_CRM_KEY = os.environ.get("GLOBALWAYS_CRM_KEY", None)

GLOBALWAYS_QUEUE_URL = os.environ.get("GLOBALWAYS_QUEUE_URL", None)
GLOBALWAYS_QUEUE_ENV = os.environ.get("GLOBALWAYS_QUEUE_ENV", None)
GLOBALWAYS_QUEUE_SOURCE = "ccdb"
