FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /build

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libpq-dev \
    && python -m venv "$VIRTUAL_ENV" \
    && pip install --no-cache-dir uv \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY uv.lock ./
COPY config ./config
COPY core ./core
COPY manage.py ./

RUN uv sync --frozen --no-dev


FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    GUNICORN_WORKERS=2

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libpq5 postgresql-client \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/config ./config
COPY --from=builder /build/core ./core
COPY --from=builder /build/manage.py ./manage.py
COPY entrypoint.sh ./entrypoint.sh

RUN chown -R app:app /app /opt/venv \
    && chmod +x /app/entrypoint.sh

USER app

EXPOSE 8000
STOPSIGNAL SIGTERM

ENTRYPOINT ["/app/entrypoint.sh"]
