# IncuBrix AI Background Music Engine — Production Container
FROM python:3.11-slim

# Install system dependencies (FFmpeg, libsndfile, curl, build essentials)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source tree and configuration
COPY . .

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEFAULT_SAMPLE_RATE=48000 \
    TARGET_LUFS=-16.0 \
    STORAGE_BACKEND=minio \
    CELERY_ENABLED=true

EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
