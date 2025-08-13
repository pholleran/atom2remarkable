#!/bin/bash

# Enable RMAPI tracing for debugging
export RMAPI_TRACE=1

# Make sure APP_ROOT is set
if [ -z "$APP_ROOT" ]; then
    # Default to /usr/src/app if not set
    export APP_ROOT="/usr/src/app"
    echo "APP_ROOT was not set, defaulting to $APP_ROOT"
fi

# Ensure we're using the correct Python path
export PYTHONPATH=$APP_ROOT:$PYTHONPATH

# rmapi configuration setup
echo "Setting up rmapi configuration..."
echo "Checking for a DEVICE_TOKEN"
echo "...DEVICE_TOKEN is set: $(if [ -n "$DEVICE_TOKEN" ]; then echo "YES"; else echo "NO"; fi)"
echo "...DEVICE_TOKEN length: ${#DEVICE_TOKEN} characters"

# Function to create rmapi config
setup_rmapi_config() {
    local config_file=""
    local usertoken=""
    
    echo "Setting up rmapi configuration file..."

    # Determine the appropriate location for the config file based on environment
    config_file="$HOME/.config/rmapi/rmapi.conf"
    echo "...Using default environment"
    
    # Ensure the directory exists
    mkdir -p "$(dirname "$config_file")"
    echo "...Creating rmapi config: $config_file"
    
    if [[ -n "$DEVICE_TOKEN" ]]; then
        # Always create a new config file with the device token and preserved usertoken
        cat > "$config_file" << EOF
devicetoken: $DEVICE_TOKEN
usertoken: $usertoken
EOF
        echo "...Created new rmapi config with devicetoken"
        
        # Ensure proper permissions
        chmod 644 "$config_file"
        echo "...rmapi configuration setup completed successfully"

        # check rmapi executable
        echo "rmapi path and permission:"
        echo "...which rmapi: $(which rmapi 2>/dev/null || echo "rmapi not found in PATH")"
        echo "...$(ls -la $(which rmapi 2>/dev/null) 2>/dev/null || echo "rmapi not found in PATH")"

        # Show config file content without the actual token
        echo "Config file exists: $(test -f "$config_file" && echo "YES" || echo "NO")"
        echo "Config file permissions: $(ls -la "$config_file")"
        echo "Config file contains devicetoken: $(grep -q "^devicetoken:" "$config_file" && echo "YES" || echo "NO")"
        cat $config_file
    else
        echo "Warning: DEVICE_TOKEN not set - rmapi authentication may fail"
        return 1
    fi
}

# Set up rmapi configuration
setup_rmapi_config

# Execute the original command
exec "$@"