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
python manage.py migrate --noinput

echo "Creating superuser ${SUPERUSER_USERNAME:-admin}..."
DJANGO_SUPERUSER_USERNAME="${SUPERUSER_USERNAME:-admin}" \
  DJANGO_SUPERUSER_PASSWORD="${SUPERUSER_PASSWORD:-admin123}" \
  DJANGO_SUPERUSER_EMAIL="${SUPERUSER_EMAIL:-admin@example.com}" \
  python manage.py createsuperuser --noinput \
  || echo "Superuser already exists"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn..."
gunicorn -c gunicorn.conf.py bot_constructor.wsgi:application
