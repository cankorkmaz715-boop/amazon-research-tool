#!/bin/bash

echo "Stopping existing services..."

pkill -f "amazon_research.runtime_service" || true
pkill -f "uvicorn amazon_research.api_gateway.app:app" || true
pkill -f "vite preview" || true
pkill -f "npm run preview" || true

sleep 2

echo "Starting runtime service..."

cd /root/amazon-tool
source venv/bin/activate
export PYTHONPATH="/root/amazon-tool/src"

nohup python -m amazon_research.runtime_service > runtime.log 2>&1 &

sleep 2

echo "Starting API gateway..."

nohup python -m uvicorn amazon_research.api_gateway.app:app \
--host 0.0.0.0 \
--port 8000 > api.log 2>&1 &

sleep 2

echo "Building frontend..."

cd /root/amazon-tool/frontend
npm run build > build.log 2>&1

echo "Starting frontend..."

nohup npm run preview -- --host 0.0.0.0 --port 3000 > frontend.log 2>&1 &

sleep 3

echo "Checking services..."

ss -tulnp | grep -E "8000|3000"

echo ""
echo "Platform restarted successfully"
echo ""
echo "API Docs:"
echo "http://167.86.105.250:8000/docs"
echo ""
echo "Frontend:"
echo "http://167.86.105.250:3000"
