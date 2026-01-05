# PhotonPath API v2.0 - Docker Configuration
# ==========================================
# 
# Build:  docker build -t photonpath-api .
# Run:    docker run -p 8000:8000 -e PORT=8000 photonpath-api
# Test:   curl http://localhost:8000/health

FROM python:3.11-slim

LABEL maintainer="PhotonPath"
LABEL version="2.1.0"
LABEL description="Biophotonics Simulation Platform API with Billing"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
# =========================

# Core API
COPY photonpath.py .
COPY api_v2.py .
COPY advanced_calculations.py .

# Databases
COPY tissue_optical_properties.json .
COPY optogenetics_db.json .

# Simulation Modules
COPY monte_carlo.py .
COPY fluorescence.py .
COPY multiwavelength.py .
COPY oximetry.py .
COPY pdt_dosimetry.py .

# Billing & Rate Limiting
COPY stripe_billing.py .
COPY rate_limiter.py .
COPY billing_endpoints.py .
COPY email_service.py .

# SDKs (optional, for distribution)
COPY photonpath_sdk.py .
COPY PhotonPathClient.m .

# Documentation
COPY README.md .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Environment variables (defaults - override in Railway)
ENV PORT=8000
ENV ENVIRONMENT=production

# Expose port
EXPOSE $PORT

# NO HEALTHCHECK - Let Railway handle it
# HEALTHCHECK is removed because it causes issues with dynamic ports

# Run the API with shell form to expand $PORT variable
CMD uvicorn api_v2:app --host 0.0.0.0 --port $PORT