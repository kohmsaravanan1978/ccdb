#!/bin/bash

mkdir -p $LOGGING_DIRECTORY
chown -R ia: $LOGGING_DIRECTORY
chown -R ia: $SHARED_STORE
exec uwsgi --ini /uwsgi.ini
