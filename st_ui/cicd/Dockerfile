# Use a lightweight Python image
FROM python:3.10-slim

# Set environment variables to reduce Python output and warnings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Update system packages and clean up
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up the working directory
WORKDIR /app

# Add the working directory to PYTHONPATH
ENV PYTHONPATH=.

# Accept arguments and pass them as environment variables
ARG GIT_RUN_NUMBER='no-run-number'
ARG GIT_COMMIT_SHA='no-commit-sha'
ENV GIT_RUN_NUMBER=$GIT_RUN_NUMBER
ENV GIT_COMMIT_SHA=$GIT_COMMIT_SHA

# Copy application code
COPY utils ./utils
COPY flow_apps ./flow_apps
COPY st_ui ./st_ui

# Copy local data
COPY local_data ./local_data

# Create user
RUN useradd -m appuser

# Set permissions for local_data
# - Give read-only access to everything in /app/local_data/*
# - Empty /app/local_data/data if it exists; otherwise create it
RUN chown -R root:root /app/local_data && \
    chmod -R 755 /app/local_data && \
    mkdir -p /app/local_data/data/saved_states && \
    rm -rf /app/local_data/data/saved_states* && \
    chown appuser:appuser /app/local_data/data && \
    chmod 775 /app/local_data/data

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r utils/requirements.txt && \
    pip install --no-cache-dir -r st_ui/requirements.txt

# Switch to a non-root user
USER appuser

# Expose Streamlit default port
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "st_ui/app.py", "--server.port=8501", "--server.enableCORS=false"]
