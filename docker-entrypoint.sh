#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER 2>/dev/null; do
    sleep 1
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis..."
while ! redis-cli -h $REDIS_HOST ping 2>/dev/null; do
    sleep 1
done
echo "Redis is ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"