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

# Stop and remove container
docker stop $TEST_INSTANCE_NAME
docker rm  $TEST_INSTANCE_NAME
