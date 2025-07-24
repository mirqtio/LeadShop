FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/home/app/.cache/ms-playwright

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        curl \
        gcc \
        g++ \
        libffi-dev \
        libssl-dev \
        libpq-dev \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create non-root user with home directory
RUN groupadd -r app && useradd -r -g app -m app
RUN chown -R app:app /app

# Install Playwright system dependencies as root first
RUN playwright install-deps chromium

# Switch to app user and install browsers in app user's home directory
USER app

# Install Playwright browsers as app user (for PRP-004 security scraper)
# This ensures browsers are accessible by the worker processes
RUN playwright install chromium

# Verify browser installation
RUN ls -la /home/app/.cache/ms-playwright/ || echo "Browser path will be created during installation"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]