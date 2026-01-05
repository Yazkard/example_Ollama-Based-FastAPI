#!/bin/sh

echo "Starting FastAPI application..."

if [ "$DEBUG_MODE" = "true" ]; then
    echo "Running in DEBUG MODE with debugpy..."
    exec python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m uvicorn main:app --host 0.0.0.0 --port 8000
else
    exec uvicorn main:app --host 0.0.0.0 --port 8000
fi
