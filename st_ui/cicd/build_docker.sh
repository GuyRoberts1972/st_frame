#!/bin/bash

# Function to determine if script is running in GitHub Actions
is_github_actions() {
  [[ -n "$GITHUB_ACTIONS" ]]
}

# Set -e only for GitHub Actions
if is_github_actions; then
  set -e
fi

# Function to check if the script has been sourced
is_sourced() {
  # If $0 (the script being executed) equals $BASH_SOURCE (the script's name), it's executed directly
  [[ "$0" != "$BASH_SOURCE" ]]
}

# Check if the script is sourced (only applies when running locally)
if ! is_github_actions && ! is_sourced; then
  echo "ERROR: This script must be sourced to set environment variables locally."
  echo "Run it as: source $0"
  exit 1
fi

# Default values for local execution
TARGET="st_ui"
DEFAULT_IMAGE_NAME=$TARGET
DEFAULT_IMAGE_TAG="local"

# Image name construction
if is_github_actions; then
  # Running in GitHub Actions
  IMAGE_NAME=$(echo "ghcr.io/${GITHUB_REPOSITORY_OWNER}/${GITHUB_REPOSITORY}/${TARGET}" | tr '[:upper:]' '[:lower:]')
else
  # Running locally
  IMAGE_NAME=$DEFAULT_IMAGE_NAME
fi

# Determine the tag
if is_github_actions; then
  if [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]; then
    # It's a pull request - tag with PR number and run ID
    IMAGE_TAG="pr-${GITHUB_EVENT_PULL_REQUEST_NUMBER}-${GITHUB_RUN_ID}"
  elif [[ "$GITHUB_REF" == "refs/heads/main" ]]; then
    # It's the main branch - tag as latest
    IMAGE_TAG="latest"
  else
    # It's on a branch - tag with branch name
    IMAGE_TAG=$(echo "$GITHUB_REF" | sed 's/refs\/heads\///')
  fi
else
  # Default tag for local execution
  IMAGE_TAG=$DEFAULT_IMAGE_TAG
fi

# Log the image name and tag for debugging
echo "Building Docker image:"
echo "  IMAGE_NAME: $IMAGE_NAME"
echo "  IMAGE_TAG: $IMAGE_TAG"

# Build the Docker image
docker build -f ./st_ui/cicd/Dockerfile --cache-from "$IMAGE_NAME:latest" -t "$IMAGE_NAME:$IMAGE_TAG" .

# Export environment variables and outputs if in GitHub Actions
if is_github_actions; then
  # Save to environment variables
  echo "IMAGE_NAME=$IMAGE_NAME" >> "$GITHUB_ENV"
  echo "IMAGE_TAG=$IMAGE_TAG" >> "$GITHUB_ENV"

  # Save to job outputs
  echo "image_name=$IMAGE_NAME" >> "$GITHUB_OUTPUT"
  echo "image_tag=$IMAGE_TAG" >> "$GITHUB_OUTPUT"
fi

# Export variables locally for the current shell session
if ! is_github_actions; then

  export IMAGE_NAME="$IMAGE_NAME"
  export IMAGE_TAG="$IMAGE_TAG"

  echo "Environment variables set:"
  echo "  IMAGE_NAME=$IMAGE_NAME"
  echo "  IMAGE_TAG=$IMAGE_TAG"
fi