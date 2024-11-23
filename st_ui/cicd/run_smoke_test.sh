#!/bin/bash

# Configurable parameters
TIMEOUT=10
CHECK_STRING="You need to enable JavaScript to run this app"
URL="http://localhost:8501"

# Function to determine if script is running in GitHub Actions
is_github_actions() {
  [[ -n "$GITHUB_ACTIONS" ]]
}

# Set -e only for GitHub Actions
if is_github_actions; then
  set -e
fi

# Function to check if the response contains the required string
check_app_response() {
    local response=$1
    echo "$response" | grep -q "$CHECK_STRING"
}

# Poll every 1 second until timeout
echo "Waiting for the app to start at $URL..."
for i in $(seq 1 $TIMEOUT); do
    RESPONSE=$(curl -s "$URL" || true)
    if check_app_response "$RESPONSE"; then
        echo "App started successfully."
        break
    fi
    echo "Waiting for app to start... ($i/$TIMEOUT)"
    sleep 1
done

# Verify if the app responded correctly
if ! check_app_response "$RESPONSE"; then
    echo "$RESPONSE"
    echo "App failed to start within $TIMEOUT seconds."
    exit 1
fi
