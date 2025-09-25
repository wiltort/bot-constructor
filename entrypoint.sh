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

echo "Creating superuser 'root'..."
DJANGO_SUPERUSER_USERNAME="root" \
  DJANGO_SUPERUSER_PASSWORD="root" \
  DJANGO_SUPERUSER_EMAIL="root@example.com" \
  python src/manage.py createsuperuser --noinput \
  || echo "Superuser already exists"

echo "Starting Django development server..."
python src/manage.py runserver 0.0.0.0:8000