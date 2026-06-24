#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until python -c "import os, psycopg2; psycopg2.connect(os.environ['DATABASE_URL'])" 2>/dev/null; do
  sleep 2
done

echo "Running ETL pipeline..."
python etl/pipeline.py

echo "Starting API..."
exec uvicorn app:app --host 0.0.0.0 --port 8000
