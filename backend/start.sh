#!/bin/sh
if [ -z "$PORT" ]; then
  PORT=8000
fi
exec uvicorn main:app --host 0.0.0.0 --port $PORT
