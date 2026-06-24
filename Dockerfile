FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x scripts/start.sh

ENV DATABASE_URL=postgresql://churn_user:churn_pass@postgres:5432/churn_db
ENV USE_DB=true
ENV DATA_PATH=data/raw/telco_churn.csv

EXPOSE 8000

CMD ["sh", "scripts/start.sh"]
