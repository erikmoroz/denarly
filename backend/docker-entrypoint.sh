#!/bin/bash
set -e

echo "Running database migrations..."
uv run python manage.py migrate --noinput

echo "Seeding legal documents..."
uv run python manage.py seed_legal_documents

if [ "$USE_S3_STORAGE" = "true" ]; then
    echo "Collecting static files to S3..."
    uv run python manage.py collectstatic --noinput
fi

echo "Starting server..."
exec "$@"
