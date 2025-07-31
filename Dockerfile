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

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create necessary directories with proper permissions
RUN mkdir -p output logs templates /root/.config/rmapi && \
    chmod 755 output logs templates && \
    chmod -R 755 /root/.config

# Set environment variables
ENV PYTHONPATH=/app
ENV OUTPUT_DIR=/app/output
ENV LOG_DIR=/app/logs
ENV FEEDS_FILE=/app/feeds.txt
ENV RECENT_HOURS=24
ENV REMARKABLE_FOLDER=AtomFeeds

# Ensure the container can write to these directories
RUN chmod -R 755 /app/output /app/logs

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (simplified - no scheduling)
CMD ["python", "main.py"]
