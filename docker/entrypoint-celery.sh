#!/bin/bash

mkdir -p $LOGGING_DIRECTORY
chown -R ia: $LOGGING_DIRECTORY
chown -R ia: $SHARED_STORE

cd /code
exec sudo --preserve-env -u ia /poetry/.venv/bin/celery -A ccdb worker -Q ccdb-default --loglevel=info
