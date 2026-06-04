FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==1.8.3"

COPY pyproject.toml poetry.lock ./
RUN poetry lock --no-update \
    && poetry install --only main

COPY . .

EXPOSE 8010
