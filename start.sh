#!/bin/sh
#

python3 manage.py migrate                  # Apply database migrations
python3 manage.py collectstatic --noinput  # Collect static files

# Start nginx
nginx

# Start jobs in a loop
sh /jobs.sh &

# Start Gunicorn processes
echo Starting uvicorn.
exec uvicorn \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level=info \
  --access-log \
  aanmelden.asgi:application
