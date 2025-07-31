#!/bin/bash

# rmapi configuration setup
echo "Setting up rmapi configuration..."
echo "Environment variables available: $(env | grep -v TOKEN | cut -d '=' -f1 | tr '\n' ' ')"
echo "DEVICE_TOKEN is set: $(if [ -n "$DEVICE_TOKEN" ]; then echo "YES"; else echo "NO"; fi)"
echo "DEVICE_TOKEN length: ${#DEVICE_TOKEN} characters"

# Determine if we're running in GitHub Actions
IS_GITHUB_ACTIONS=$([[ -n "${GITHUB_ACTIONS}" ]] && echo "true" || echo "false")
echo "Running in GitHub Actions: $IS_GITHUB_ACTIONS"

# Define config file paths based on environment
if [[ "$IS_GITHUB_ACTIONS" == "true" ]]; then
    # GitHub Actions paths - check multiple locations with priority for GitHub Actions paths
    CONFIG_PATHS=(
        "/home/app/.config/rmapi/rmapi.conf"
        "/home/app/.rmapi"
        "/github/home/.config/rmapi/rmapi.conf"
        "/github/home/.rmapi"
        "/root/.config/rmapi/rmapi.conf"
        "/root/.rmapi"
    )
    DEFAULT_CONFIG_DIR="/home/app/.config/rmapi"
else
    # Local environment paths
    CONFIG_PATHS=(
        "/root/.config/rmapi/rmapi.conf"
        "/root/.rmapi"
        "/home/app/.config/rmapi/rmapi.conf"
        "/home/app/.rmapi"
    )
    DEFAULT_CONFIG_DIR="/root/.config/rmapi"
fi

echo "Config search paths: ${CONFIG_PATHS[*]}"
echo "Default config directory: $DEFAULT_CONFIG_DIR"

# Function to update or create rmapi config
setup_rmapi_config() {
    local config_file=""
    local config_exists=false
    
    # Check if any config file already exists
    for path in "${CONFIG_PATHS[@]}"; do
        echo "Checking for config at: $path"
        if [[ -f "$path" ]]; then
            config_file="$path"
            config_exists=true
            echo "Found existing rmapi config: $config_file"
            break
        fi
    done
    
    # If no config exists, create it in the appropriate standard location
    if [[ "$config_exists" == false ]]; then
        config_file="$DEFAULT_CONFIG_DIR/rmapi.conf"
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
        
        # Test rmapi connectivity
        echo "Testing rmapi connectivity..."
        rmapi version
        echo "Testing rmapi authentication..."
        timeout 10 rmapi ls || echo "rmapi ls command timed out or failed"
    else
        echo "Warning: DEVICE_TOKEN not set - rmapi authentication may fail"
        return 1
    fi
}

# Set up rmapi configuration
setup_rmapi_config

# Create symlinks between potential config locations to ensure accessibility
create_config_symlinks() {
    echo "Creating symlinks for rmapi config files to ensure accessibility..."
    
    # Get the actual config file path that was created/updated
    local actual_config=$(find /root/.config/rmapi /home/app/.config/rmapi -name "rmapi.conf" -type f 2>/dev/null | head -1)
    
    if [[ -n "$actual_config" ]]; then
        echo "Found actual config at: $actual_config"
        
        # Create directory structure for potential symlink targets
        mkdir -p /root/.config/rmapi
        mkdir -p /home/app/.config/rmapi
        
        # Create symlinks if the target doesn't exist and isn't the actual config
        if [[ "$actual_config" != "/root/.config/rmapi/rmapi.conf" && ! -e "/root/.config/rmapi/rmapi.conf" ]]; then
            ln -sf "$actual_config" "/root/.config/rmapi/rmapi.conf"
            echo "Created symlink: /root/.config/rmapi/rmapi.conf -> $actual_config"
        fi
        
        if [[ "$actual_config" != "/home/app/.config/rmapi/rmapi.conf" && ! -e "/home/app/.config/rmapi/rmapi.conf" ]]; then
            ln -sf "$actual_config" "/home/app/.config/rmapi/rmapi.conf"
            echo "Created symlink: /home/app/.config/rmapi/rmapi.conf -> $actual_config"
        fi
        
        # Also link to ~/.rmapi format (old format)
        if [[ ! -e "/root/.rmapi" ]]; then
            ln -sf "$actual_config" "/root/.rmapi"
            echo "Created symlink: /root/.rmapi -> $actual_config"
        fi
        
        if [[ ! -e "/home/app/.rmapi" ]]; then
            ln -sf "$actual_config" "/home/app/.rmapi"
            echo "Created symlink: /home/app/.rmapi -> $actual_config"
        fi
    else
        echo "Warning: Could not find any rmapi.conf file to create symlinks for"
    fi
}

# Create symlinks for config files
create_config_symlinks

# Final check - see what rmapi sees when it looks for config
echo "Checking rmapi version one more time:"
rmapi version

# Execute the original command
exec "$@"