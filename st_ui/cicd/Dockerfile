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
ARG GITHUB_RUN_NUMBER='no-run-number'
ARG GITHUB_REF='no-commit-ref'
ARG GITHUB_SHA='no-commit-sha'
ENV GITHUB_RUN_NUMBER=$GITHUB_RUN_NUMBER
ENV GITHUB_REF=$GITHUB_REF
ENV GITHUB_SHA=$GITHUB_SHA

# Copy application code and config
COPY utils ./utils
COPY flow_apps ./flow_apps
COPY st_ui ./st_ui
COPY .streamlit/config.toml ./.streamlit/config.toml

# Create version info file
RUN echo "\n[build]" >> ./version_info.toml && \
    echo "github_run_number = \"$GITHUB_RUN_NUMBER\"" >> ./version_info.toml && \
    echo "github_ref = \"$GITHUB_REF\"" >> ./version_info.toml  && \
    echo "github_sha = \"$GITHUB_SHA\"" >> ./version_info.toml

# Copy local data
COPY local_data ./local_data

# Create user
RUN useradd -m appuser

# Set permissions for local_data
# - Grant read-only access to all directories and files under /app/local_data/*
# - Ensure /app/local_data/data exists and is writable by appuser
# - Ensure /app/local_data/data/saved_states exists, is empty, and writable by appuser

RUN chown -R root:root /app/local_data && \
    chmod -R 755 /app/local_data && \
    mkdir -p /app/local_data/data/saved_states && \
    rm -rf /app/local_data/data/saved_states/* && \
    chown appuser:appuser /app/local_data/data && \
    chmod 775 /app/local_data/data && \
    chown appuser:appuser /app/local_data/data/saved_states && \
    chmod 775 /app/local_data/data/saved_states

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r utils/requirements.txt && \
    pip install --no-cache-dir -r flow_apps/requirements.txt && \
    pip install --no-cache-dir -r st_ui/requirements.txt

# Switch to a non-root user
USER appuser

# Expose Streamlit default port
EXPOSE 8080

# Command to run the Streamlit app
CMD ["streamlit", "run", "st_ui/app.py", "--server.port=8080", "--server.enableCORS=false"]
