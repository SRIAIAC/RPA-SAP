FROM python:3.12-slim

# Tesseract is required for the Mailroom feature's real OCR (see
# app/services/ocr.py) — installed here so the container has full feature
# parity with local dev instead of silently degrading to OCR_ERROR strings.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as an unprivileged user, not root — the app only ever needs to write
# its own SQLite file (local dev) or talk to Postgres (Docker); it never
# needs root inside the container.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/app/data/invoices \
    && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
