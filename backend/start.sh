#!/bin/sh
echo "PORT variable is: $PORT"
if [ -z "$PORT" ]; then
  echo "PORT not set, using 8000"
  PORT=8000
fi
exec uvicorn main:app --host 0.0.0.0 --port $PORT
