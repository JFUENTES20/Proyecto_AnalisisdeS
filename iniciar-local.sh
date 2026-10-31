#!/bin/sh
set -eu
cd "$(dirname "$0")"
. ./.local/demo.env
if [ "$#" -eq 0 ]; then
    set -- runserver "${RUNSERVER_ADDR:-127.0.0.1:8000}" --noreload
fi
exec .venv/bin/python manage.py "$@"
