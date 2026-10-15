# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
# Optional CA mount is useful for managed build environments. Ordinary Railway
# builds use the image's normal verified trust store.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir --require-hashes -r requirements.txt
COPY . .
RUN DEBUG=1 python manage.py collectstatic --noinput \
    && useradd --create-home --uid 10001 yaara \
    && chmod -R a+rX /app \
    && chmod +x scripts/start.sh
USER yaara
ENV DEBUG=0
CMD ["sh", "scripts/start.sh"]
