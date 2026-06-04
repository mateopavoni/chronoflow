# ChronoFlow API — Dockerfile
# Build: docker build -t chronoflow-api .
# Used by docker-compose.yml (service: api)

FROM python:3.11-slim

# Prevent Python from buffering stdout (important for container logs)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install system dependencies (asyncpg needs libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache: only rebuilds on requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Startup: run Alembic migrations, then start uvicorn.
# Note: In production you'd separate migration from app start.
# Convenient for local development.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
