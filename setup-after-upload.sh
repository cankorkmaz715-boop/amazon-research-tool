#!/bin/bash
# Run this on the VPS after you have uploaded your project files to /root/amazon-tool
set -e
cd /root/amazon-tool

echo "=== Checking files ==="
if [ ! -f package.json ]; then
  echo "ERROR: package.json not found. Upload your project files first."
  exit 1
fi
ls -la

echo ""
echo "=== Installing dependencies ==="
npm install

echo ""
echo "=== Building project ==="
npm run build

echo ""
echo "=== Starting with PM2 ==="
pm2 delete amazon-tool 2>/dev/null || true
pm2 start npm --name "amazon-tool" -- start
pm2 save

echo ""
echo "=== Done. App status: ==="
pm2 list
