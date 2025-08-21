#!/bin/bash

mkdir -p $LOGGING_DIRECTORY
chown -R ia: $LOGGING_DIRECTORY

cd /code
exec sudo --preserve-env -u ia /poetry/.venv/bin/celery -A ccdb beat --loglevel=info --pidfile= -s /tmp/celery_beat_db
