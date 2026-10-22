#!/bin/sh
set -eu

echo "Applying database migrations before starting Render web service..."
python manage.py migrate --noinput
exec sh scripts/start.sh
