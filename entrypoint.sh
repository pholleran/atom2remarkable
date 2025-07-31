#!/bin/bash

# Create rmapi configuration
echo "Creating rmapi configuration..."

mkdir -p /root/.config/rmapi

if [ -n "$DEVICE_TOKEN" ]; then
    echo "devicetoken: $DEVICE_TOKEN" > /root/.config/rmapi/rmapi.conf
    echo "usertoken: " >> /root/.config/rmapi/rmapi.conf
    echo "rmapi configuration created successfully"
else
    echo "Warning: DEVICE_TOKEN not set"
fi

# Execute the original command
exec "$@"
