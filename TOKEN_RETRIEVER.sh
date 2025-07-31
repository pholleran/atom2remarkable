#!/bin/bash

# TOKEN_RETRIEVER.sh - Extract reMarkable device token from rmapi configuration
# This script helps users retrieve their device token for use with atom2remarkable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}SUCCESS: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_info() {
    echo -e "$1"
}

# Check if rmapi is installed
check_rmapi() {
    if ! command -v rmapi &> /dev/null; then
        print_error "rmapi is not installed or not in PATH"
        print_info ""
        print_info "Please install rmapi from: https://github.com/ddvk/rmapi"
        print_info ""
        print_info "Installation instructions:"
        print_info "1. Download the latest release for your platform"
        print_info "2. Extract and move to a directory in your PATH (e.g., /usr/local/bin/)"
        print_info "3. Make it executable: chmod +x /usr/local/bin/rmapi"
        exit 1
    fi
}

# Find rmapi configuration file
find_config_file() {
    local config_file=""
    
    # Check for .rmapi in HOME directory first
    if [[ -f "$HOME/.rmapi" ]]; then
        config_file="$HOME/.rmapi"
        print_info "Found rmapi config: $config_file" >&2
        echo "$config_file"
        return 0
    elif [[ -f "$HOME/.config/rmapi/rmapi.conf" ]]; then
        # Check common location
        config_file="$HOME/.config/rmapi/rmapi.conf"
        print_info "Found rmapi config: $config_file" >&2
        echo "$config_file"
        return 0
    else
        # Search entire filesystem for rmapi.conf (this might take a while)
        print_info "Searching for rmapi.conf files on the system..." >&2
        
        # Try common locations first before doing a full search
        local common_locations=(
            "/etc/rmapi.conf"
            "/usr/local/etc/rmapi.conf"
            "/opt/rmapi/rmapi.conf"
            "$HOME/.rmapi.conf"
            "$HOME/Library/Application Support/rmapi/rmapi.conf"
        )
        
        for location in "${common_locations[@]}"; do
            if [[ -f "$location" ]]; then
                config_file="$location"
                print_info "Found rmapi config: $config_file" >&2
                echo "$config_file"
                return 0
            fi
        done
        
        # If not found in common locations, do a broader search
        if [[ -z "$config_file" ]]; then
            print_info "Searching common directories for rmapi.conf..." >&2
            
            # Search in user's home directory tree
            if [[ -d "$HOME" ]]; then
                local found_file=$(find "$HOME" -name "rmapi.conf" -type f 2>/dev/null | head -1)
                if [[ -n "$found_file" ]]; then
                    config_file="$found_file"
                    print_info "Found rmapi config: $config_file" >&2
                    echo "$config_file"
                    return 0
                fi
            fi
        fi
    fi
    
    # If we get here, no config file was found
    print_error "No rmapi configuration file found"
    print_info ""
    print_info "Please run rmapi for the first time to authenticate:"
    print_info "1. Run: rmapi"
    print_info "2. Follow the authentication prompts"
    print_info "3. Once authenticated, run this script again"
    print_info ""
    print_info "rmapi will create a configuration file containing your device token."
    return 1
}

# Extract device token from config file
extract_device_token() {
    local config_file="$1"
    
    if [[ ! -r "$config_file" ]]; then
        print_error "Cannot read config file: $config_file"
        print_info "Please check file permissions."
        return 1
    fi
    
    # Look for devicetoken line
    local device_token=$(grep "^devicetoken:" "$config_file" 2>/dev/null | cut -d' ' -f2- | tr -d ' ')
    
    if [[ -z "$device_token" ]]; then
        print_error "No device token found in config file: $config_file"
        print_info ""
        print_info "The config file exists but doesn't contain a device token."
        print_info "Please re-authenticate with rmapi:"
        print_info "1. Run: rmapi"
        print_info "2. Follow the authentication prompts"
        return 1
    fi
    
    echo "$device_token"
    return 0
}

# Main function
main() {
    print_info "reMarkable Device Token Retriever"
    print_info "=================================="
    print_info ""
    
    # Check if rmapi is installed
    print_info "Checking for rmapi installation..."
    check_rmapi
    print_success "rmapi is installed"
    print_info ""
    
    # Find configuration file
    print_info "Looking for rmapi configuration..."
    local config_file
    config_file=$(find_config_file)
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
    print_info ""
    
    # Extract device token
    print_info "Extracting device token..."
    local device_token
    device_token=$(extract_device_token "$config_file")
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
    
    if [[ -n "$device_token" ]]; then
        print_success "Device token found!"
        print_info ""
        print_info "Set a DEVICE_TOKEN environment variable to:"
        print_info "=================================="
        echo "$device_token"
        print_info "=================================="
    else
        print_error "Failed to extract device token"
        exit 1
    fi
}

# Run main function
main "$@"
