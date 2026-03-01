#!/bin/sh
set -e

echo "Waiting for DB."
while ! python -c "import socket; socket.create_connection(('${DB_HOST:-db}', ${DB_PORT:-5432}))" 2>/dev/null; do
    sleep 1
done
echo "DB is ready."

python manage.py migrate --noinput # Run migrations
python manage.py createsuperuser --noinput 2>/dev/null || true # Create superuser if it doesn't exist, ignore if it does

# Reset stale or incomplete interview sessions in DB
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from app.models import InterviewSession
updated = InterviewSession.objects.filter(status__in=['running','extracting','clustering','summarizing']).update(status='failed')
if updated: print(f'Reset {updated} stale session(s) to failed')
"


exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300
