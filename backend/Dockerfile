FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INGEST_CACHE_DIR=/cache

WORKDIR /app

# En local, compose pasa requirements-dev.txt para tener también pytest.
ARG REQUIREMENTS=requirements.txt
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r ${REQUIREMENTS}

COPY . .

RUN useradd --create-home appuser && mkdir /cache && chown appuser /cache
USER appuser

EXPOSE 8000
# Render inyecta PORT; en local se usa 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
