#!/bin/bash

# Start Renderix service in the background
echo "Starting Renderix service..."
/usr/bin/renderix &
RENDERIX_PID=$!

# Wait a moment for Renderix to start
sleep 2

export NAMECHEAP_API_KEY=${NAMECHEAP_API_KEY}
export NAMECHEAP_USER=${NAMECHEAP_USER}
export NAMECHEAP_CLIENT_IP=${NAMECHEAP_CLIENT_IP}

# Start Caddy
echo "Starting Caddy..."
/usr/bin/caddy start

# Start the FastAPI application
echo "Starting FastAPI application..."
/usr/local/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000