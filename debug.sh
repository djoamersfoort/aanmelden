#!/usr/bin/env sh

exec uvicorn \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level=info \
  --access-log \
  --reload \
  --reload-include *.html \
  --reload-include *.css \
  --reload-include *.js \
  aanmelden.asgi:application
