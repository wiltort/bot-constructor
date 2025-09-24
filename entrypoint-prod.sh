#!/bin/sh

set -e

# Ожидание готовности PostgreSQL
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL started"

# Ожидание Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done

echo "Redis started"

echo "Applying Django migrations..."
python src/manage.py migrate --noinput

echo "Collecting static files..."
python src/manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn bot_constructor.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120