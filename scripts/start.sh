#!/bin/sh
set -eu
# Railway's pre-deploy command owns migrations. This process only serves HTTP.
exec gunicorn yaara.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --access-logformat '%(t)s method=%(m)s status=%(s)s duration_us=%(D)s bytes=%(B)s' \
    --error-logfile -
