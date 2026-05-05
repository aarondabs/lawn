FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy alembic "psycopg[binary]" pydantic-settings httpx apscheduler

COPY src ./src
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "lawn_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
