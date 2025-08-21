import os

from .base import *  # noqa

if os.environ.get("CCDB_DATABASE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql_psycopg2",
            "NAME": "ccdb",
            "USER": "ccdb",
            "PASSWORD": "ccdb",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

SECRET_KEY = "viziv%r0_&srs51f583$evb2a58g#v8iczcov*6p9%ywxau!%-"
DEBUG = True
SECURE_SSL_REDIRECT = False

# Do not log to files in CI
LOGGING["handlers"].pop("file")  # noqa
for logger in LOGGING["loggers"]:  # noqa
    if "handlers" in LOGGING["loggers"][logger]:  # noqa
        LOGGING["loggers"][logger]["handlers"].remove("file")  # noqa
