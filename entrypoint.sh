#!/bin/sh

set -e

echo "Applying Django migrations..."
python src/manage.py migrate --noinput

echo "Starting Django development server..."
python src/manage.py runserver 0.0.0.0:8000