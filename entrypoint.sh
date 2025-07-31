#!/bin/bash

# rmapi configuration setup
echo "Setting up rmapi configuration..."
echo "Environment variables available: $(env | grep -v TOKEN | cut -d '=' -f1 | tr '\n' ' ')"
echo "DEVICE_TOKEN is set: $(if [ -n "$DEVICE_TOKEN" ]; then echo "YES"; else echo "NO"; fi)"
echo "DEVICE_TOKEN length: ${#DEVICE_TOKEN} characters"

# Determine if we're running in GitHub Actions
IS_GITHUB_ACTIONS=$([[ -n "${GITHUB_ACTIONS}" ]] && echo "true" || echo "false")
echo "Running in GitHub Actions: $IS_GITHUB_ACTIONS"

# First, let's try to determine exactly where rmapi is looking for its config
echo "Checking where rmapi looks for config..."
RMAPI_DEBUG_OUTPUT=$(rmapi --debug ls 2>&1 || echo "rmapi debug command failed")
echo "rmapi debug output: $RMAPI_DEBUG_OUTPUT"

# Extract any config paths mentioned in the debug output
CONFIG_PATHS_FROM_DEBUG=$(echo "$RMAPI_DEBUG_OUTPUT" | grep -o -E '/(home|root|github)/[^ ]*rmapi[^ ]*' || echo "")
if [[ -n "$CONFIG_PATHS_FROM_DEBUG" ]]; then
    echo "Extracted config paths from debug: $CONFIG_PATHS_FROM_DEBUG"
fi

# Get the current user's home directory
CURRENT_HOME=$(eval echo ~$(whoami))
echo "Current user's home directory: $CURRENT_HOME"

# Define config file paths based on environment
if [[ "$IS_GITHUB_ACTIONS" == "true" ]]; then
    # GitHub Actions paths - with more possibilities, including what we found from debug
    CONFIG_PATHS=(
        # GitHub Actions runner paths
        "$CURRENT_HOME/.config/rmapi/rmapi.conf"
        "$CURRENT_HOME/.rmapi"
        "/github/home/.config/rmapi/rmapi.conf"
        "/github/home/.rmapi"
        # Docker user paths
        "/home/app/.config/rmapi/rmapi.conf"
        "/home/app/.rmapi"
        # Root paths
        "/root/.config/rmapi/rmapi.conf" 
        "/root/.rmapi"
        # Near binary location
        "/usr/local/etc/rmapi/rmapi.conf"
        "/usr/local/etc/rmapi.conf"
        "/etc/rmapi/rmapi.conf"
        "/etc/rmapi.conf"
    )
    DEFAULT_CONFIG_DIR="$CURRENT_HOME/.config/rmapi"
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

# Add any paths we found from debug
if [[ -n "$CONFIG_PATHS_FROM_DEBUG" ]]; then
    # Convert newline-separated list to array and add to CONFIG_PATHS
    while IFS= read -r line; do
        CONFIG_PATHS+=("$line")
    done <<< "$CONFIG_PATHS_FROM_DEBUG"
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
        # Ensure the directory exists
        mkdir -p "$DEFAULT_CONFIG_DIR" 2>/dev/null || {
            echo "Failed to create $DEFAULT_CONFIG_DIR, trying alternate locations"
            # Try alternative locations if the default fails
            if [[ -w "/root/.config" ]]; then
                DEFAULT_CONFIG_DIR="/root/.config/rmapi"
                mkdir -p "$DEFAULT_CONFIG_DIR"
            elif [[ -w "/home/app" ]]; then
                DEFAULT_CONFIG_DIR="/home/app/.config/rmapi"
                mkdir -p "$DEFAULT_CONFIG_DIR"
            elif [[ -w "/usr/local/etc" ]]; then
                DEFAULT_CONFIG_DIR="/usr/local/etc/rmapi"
                mkdir -p "$DEFAULT_CONFIG_DIR"
            else
                # Use temp directory as last resort
                DEFAULT_CONFIG_DIR="/tmp/rmapi"
                mkdir -p "$DEFAULT_CONFIG_DIR"
            fi
        }
        
        config_file="$DEFAULT_CONFIG_DIR/rmapi.conf"
        echo "Creating new rmapi config: $config_file"
        
        # Verify we can write to this location
        touch "$config_file" 2>/dev/null || {
            echo "Cannot write to $config_file, falling back to /tmp"
            config_file="/tmp/rmapi.conf"
            touch "$config_file"
        }
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
    local actual_config=$(find "$DEFAULT_CONFIG_DIR" -name "rmapi.conf" -type f 2>/dev/null | head -1)
    
    if [[ -n "$actual_config" ]]; then
        echo "Found actual config at: $actual_config"
        
        # Get a list of all possible config locations
        local all_possible_locations=(
            # User home locations
            "$CURRENT_HOME/.config/rmapi/rmapi.conf"
            "$CURRENT_HOME/.rmapi"
            # GitHub Actions runner paths
            "/github/home/.config/rmapi/rmapi.conf"
            "/github/home/.rmapi"
            # Docker user paths
            "/home/app/.config/rmapi/rmapi.conf"
            "/home/app/.rmapi"
            # Root paths
            "/root/.config/rmapi/rmapi.conf" 
            "/root/.rmapi"
            # System-wide config locations
            "/usr/local/etc/rmapi/rmapi.conf"
            "/usr/local/etc/rmapi.conf"
            "/etc/rmapi/rmapi.conf"
            "/etc/rmapi.conf"
        )
        
        # Create symlinks to all possible locations
        for target in "${all_possible_locations[@]}"; do
            if [[ "$actual_config" != "$target" && ! -e "$target" ]]; then
                # Create the directory if needed
                mkdir -p "$(dirname "$target")" 2>/dev/null || true
                
                # Create symlink
                ln -sf "$actual_config" "$target" 2>/dev/null || echo "Failed to create symlink: $target"
                echo "Created symlink: $target -> $actual_config"
            fi
        done
        
        # Make sure everyone can read the config file
        chmod 644 "$actual_config"
        echo "Set permissions on $actual_config to ensure readability"
        
        # Also create a copy in the current user's home directory
        mkdir -p "$CURRENT_HOME/.config/rmapi" 2>/dev/null || true
        if [[ "$actual_config" != "$CURRENT_HOME/.config/rmapi/rmapi.conf" ]]; then
            cp "$actual_config" "$CURRENT_HOME/.config/rmapi/rmapi.conf" 2>/dev/null || echo "Failed to copy config to $CURRENT_HOME/.config/rmapi/rmapi.conf"
            echo "Created copy: $CURRENT_HOME/.config/rmapi/rmapi.conf"
        fi
        
    else
        echo "WARNING: Could not find the config file that was just created. This is unexpected."
        echo "Attempting to find any rmapi.conf file in the system..."
        
        # Try to find any config file in the system
        local found_config=$(find / -name "rmapi.conf" -type f 2>/dev/null | head -1)
        if [[ -n "$found_config" ]]; then
            echo "Found a config file at: $found_config"
        else
            echo "CRITICAL ERROR: No rmapi.conf file found in the system."
        fi
    fi
}

# Create symlinks for config files
create_config_symlinks

# Final check - see what rmapi sees when it looks for config
echo "Checking rmapi version one more time:"
rmapi version

# Execute the original command
exec "$@"