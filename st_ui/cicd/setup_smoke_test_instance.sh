#!/bin/bash

# Defaults
TEST_INSTANCE_NAME='streamlit-test'

# Function to determine if script is running in GitHub Actions
is_github_actions() {
  [[ -n "$GITHUB_ACTIONS" ]]
}

# Set -e only for GitHub Actions
if is_github_actions; then
  set -e
fi

# Run the image
echo "running $IMAGE_NAME:${IMAGE_TAG:-latest}"
docker run -d --name $TEST_INSTANCE_NAME -p 8501:8501 $IMAGE_NAME:${IMAGE_TAG:-latest}
