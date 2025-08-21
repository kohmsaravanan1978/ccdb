from pathlib import Path

from .base import *  # noqa

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

CELERY_TASK_ALWAYS_EAGER = False

DATABASES["TEST"] = {  # noqa
    "ENGINE": "django.db.backends.postgresql_psycopg2",
    "NAME": "test-ccdb",
    "USER": "ccdb",
    "PASSWORD": "ccdb",
    "HOST": "postgres",
}
# dev can run sqlite
if not DATABASES["default"].get("USER"):
    DATABASES["default"] = {  # noqa
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": Path(BASE_DIR) / "db.sqlite3",
    }

LOGGING["handlers"]["file"] = {  # noqa
    "class": "logging.StreamHandler",
    "level": "DEBUG",
    "formatter": "normal",
}

# debug toolbar
try:
    import debug_toolbar  # noqa

    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

print(INSTALLED_APPS)
