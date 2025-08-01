FROM python:3.11-slim

# Install system dependencies for WeasyPrint and rmapi
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install rmapi for reMarkable Cloud integration - detect architecture at build time
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ]; then \
        RMAPI_ARCH=arm64; \
    elif [ "$ARCH" = "x86_64" ]; then \
        RMAPI_ARCH=amd64; \
    else \
        echo "Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    wget -O /tmp/rmapi.tar.gz https://github.com/ddvk/rmapi/releases/latest/download/rmapi-linux-${RMAPI_ARCH}.tar.gz && \
    tar -xzf /tmp/rmapi.tar.gz -C /usr/local/bin/ && \
    chmod +x /usr/local/bin/rmapi && \
    rm /tmp/rmapi.tar.gz

# Copy requirements to a specific location
COPY requirements.txt /usr/src/app/requirements.txt
RUN pip install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy application code to a specific location
COPY . /usr/src/app

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create necessary directories with proper permissions for all possible config locations
RUN mkdir -p /usr/src/app/output /usr/src/app/logs /usr/src/app/templates \
    /root/.config/rmapi \
    /home/app/.config/rmapi \
    /home/runner/.config/rmapi \
    /github/home/.config/rmapi \
    /usr/local/etc/rmapi \
    /etc/rmapi && \
    chmod 777 /usr/src/app/output /usr/src/app/logs /usr/src/app/templates && \
    chmod -R 777 /root/.config && \
    chmod -R 777 /home/app/.config && \
    chmod -R 777 /home/runner/.config 2>/dev/null || true && \
    chmod -R 777 /github 2>/dev/null || true && \
    chmod -R 777 /usr/local/etc/rmapi && \
    chmod -R 777 /etc/rmapi

# Create backup directories for config files
RUN mkdir -p /tmp/rmapi && chmod 777 /tmp/rmapi

# Set environment variables with absolute paths
ENV PYTHONPATH=/usr/src/app
ENV APP_ROOT=/usr/src/app
ENV OUTPUT_DIR=/usr/src/app/output
ENV LOG_DIR=/usr/src/app/logs
ENV FEEDS_FILE=/usr/src/app/feeds.txt
ENV RECENT_HOURS=24
ENV REMARKABLE_FOLDER=AtomFeeds

# Ensure the container can write to these directories
RUN chmod -R 755 /usr/src/app/output /usr/src/app/logs

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command with absolute path
CMD ["python", "/usr/src/app/main.py"]
