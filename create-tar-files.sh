#!/bin/bash

# Script to create Docker image tar files for offline deployment
# This script saves the built Docker images to tar files in the tar-files directory

set -e  # Exit on any error

echo "Creating Docker image tar files for offline deployment..."

# Create tar-files directory if it doesn't exist
mkdir -p tar-files

# Build the Docker images first (if not already built)
echo "Building Docker images..."
docker compose build

# Tag images with clean project-service naming
echo "Tagging images with clean names..."
docker tag digitalisation-toolkit-digitalisation_toolkit-frontend:latest digitalisation-toolkit-frontend:latest
docker tag digitalisation-toolkit-digitalisation_toolkit-backend:latest digitalisation-toolkit-backend:latest

# Save images to tar files
echo "Saving frontend image to tar file..."
docker save digitalisation-toolkit-frontend:latest -o tar-files/digitalisation-toolkit-frontend.tar

echo "Saving backend image to tar file (this may take several minutes due to size)..."
docker save digitalisation-toolkit-backend:latest -o tar-files/digitalisation-toolkit-backend.tar

echo "Saving nginx image to tar file..."
docker save nginx:1.27.2-alpine -o tar-files/nginx-1.27.2-alpine.tar

# Display results
echo ""
echo "Tar files created successfully:"
ls -lh tar-files/

echo ""
echo "To use these tar files for offline deployment:"
echo "1. Copy the tar-files directory to your offline environment"
echo "2. Load the images with:"
echo "   docker load -i tar-files/digitalisation-toolkit-frontend.tar"
echo "   docker load -i tar-files/digitalisation-toolkit-backend.tar"
echo "   docker load -i tar-files/nginx-1.27.2-alpine.tar"
echo "3. Run with: docker compose -f docker-compose.offline.yml up -d"
echo ""
echo "Done!"