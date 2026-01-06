FROM python:3.11-slim

LABEL maintainer="PhotonPath"
LABEL version="2.1.0"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Core API
COPY photonpath.py .
COPY api_v2.py .
COPY advanced_calculations.py .

# Landing page
COPY index.html .

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

# SDKs
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