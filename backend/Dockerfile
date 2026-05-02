# ── DocMind Backend Dockerfile ────────────────────────────────────────────────
# Multi-arch (linux/amd64 + linux/arm64) — runs on Raspberry Pi 4/5
FROM python:3.11-slim

# System dependencies: libpq-dev and gcc for psycopg3, build tools for bcrypt
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer — only rebuilds when requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default: run without --reload (production)
# docker-compose.yml overrides with --reload for development hot-reloading
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
