FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY tests ./tests
RUN python -m compileall -q src/

COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 8000

CMD ["/app/docker-entrypoint.sh"]

# dev stage — extends base with test deps.
# Used by the api-test service in docker-compose.dev.yml.
# Source is volume-mounted in dev so no rebuild needed after code changes.
FROM base AS dev

RUN pip install --no-cache-dir -e ".[dev]"
