#!/bin/bash

# Build the Docker image
echo "Building atom2remarkable Docker image..."
docker build -t atom2remarkable .

# Run the application (uses entrypoint and default command from Dockerfile)
echo "Running atom2remarkable application..."
docker run --rm --env-file .env atom2remarkable
