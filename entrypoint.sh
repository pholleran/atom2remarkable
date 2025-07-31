#!/bin/bash

# rmapi configuration setup
echo "Setting up rmapi configuration..."
echo "Environment variables available: $(env | grep -v TOKEN | cut -d '=' -f1 | tr '\n' ' ')"
echo "DEVICE_TOKEN is set: $(if [ -n "$DEVICE_TOKEN" ]; then echo "YES"; else echo "NO"; fi)"
echo "DEVICE_TOKEN length: ${#DEVICE_TOKEN} characters"

# Define config file paths (check multiple locations like TOKEN_RETRIEVER.sh)
CONFIG_PATHS=(
    "/root/.rmapi"
    "/root/.config/rmapi/rmapi.conf"
)

# Function to update or create rmapi config
setup_rmapi_config() {
    local config_file=""
    local config_exists=false
    
    # Check if any config file already exists
    for path in "${CONFIG_PATHS[@]}"; do
        if [[ -f "$path" ]]; then
            config_file="$path"
            config_exists=true
            echo "Found existing rmapi config: $config_file"
            break
        fi
    done
    
    # If no config exists, create it in the standard location
    if [[ "$config_exists" == false ]]; then
        config_file="/root/.config/rmapi/rmapi.conf"
        mkdir -p "$(dirname "$config_file")"
        echo "Creating new rmapi config: $config_file"
    fi
    
    if [[ -n "$DEVICE_TOKEN" ]]; then
        if [[ "$config_exists" == true ]]; then
            # Update existing config file - replace devicetoken line or add if missing
            if grep -q "^devicetoken:" "$config_file"; then
                # Replace existing devicetoken line
                sed -i "s/^devicetoken:.*/devicetoken: $DEVICE_TOKEN/" "$config_file"
                echo "Updated devicetoken in existing config"
            else
                # Add devicetoken line
                echo "devicetoken: $DEVICE_TOKEN" >> "$config_file"
                echo "Added devicetoken to existing config"
            fi
        else
            # Create new config file
            cat > "$config_file" << EOF
devicetoken: $DEVICE_TOKEN
usertoken: 
EOF
            echo "Created new rmapi config with devicetoken"
        fi
        
        # Ensure proper permissions
        chmod 600 "$config_file"
        echo "rmapi configuration setup completed successfully"
        
        # Show config file content without the actual token
        echo "Config file exists: $(test -f "$config_file" && echo "YES" || echo "NO")"
        echo "Config file permissions: $(ls -la "$config_file" | awk '{print $1}')"
        echo "Config file contains devicetoken: $(grep -q "^devicetoken:" "$config_file" && echo "YES" || echo "NO")"
    else
        echo "Warning: DEVICE_TOKEN not set - rmapi authentication may fail"
        return 1
    fi
}

# Set up rmapi configuration
setup_rmapi_config

# Execute the original command
exec "$@"