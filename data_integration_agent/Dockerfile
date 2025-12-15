# =============================================================================
# LLL Data Integration Agent - Dockerfile
# =============================================================================
# Compact multi-stage build using Python 3.12 (stable with ADK)
# =============================================================================

FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN pip install --no-cache-dir --upgrade pip wheel

# Copy and install requirements
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# =============================================================================
# Production image
# =============================================================================

FROM python:3.12-slim-bookworm

WORKDIR /app

# Install wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code into a subdirectory for proper ADK agent structure
# ADK expects: <agents_dir>/<agent_name>/agent.py with root_agent
COPY agent.py __init__.py tools.py guardrails.py session_config.py ./data_integration_agent/

# Copy server.py to the root (it's not part of the agent module)
COPY server.py .

# Environment variables (overridden by Secret Manager in Cloud Run)
# Note: AUDIT_LOG_DIR removed - audit logs now stored in BigQuery
# Note: SESSION_DB_URL should be set via Secret Manager for persistent sessions
ENV PORT=8080 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

# Run the server directly (server.py reads PORT from environment)
CMD ["python", "server.py"]
