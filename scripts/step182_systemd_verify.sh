#!/usr/bin/env bash
# Step 182: Verify systemd service installation and state.
# Run after: sudo cp deploy/amazon-research.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable amazon-research && sudo systemctl start amazon-research

set -e

SERVICE=amazon-research

# Check service file exists
if [[ ! -f /etc/systemd/system/${SERVICE}.service ]]; then
  echo "service installed: FAIL (file not found)"
  exit 1
fi
echo "service installed: OK"

# Check enabled
if ! systemctl is-enabled --quiet "${SERVICE}" 2>/dev/null; then
  echo "service enabled: FAIL"
  exit 1
fi
echo "service enabled: OK"

# Check running
if ! systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
  echo "service running: FAIL"
  echo "--- systemctl status ${SERVICE} ---"
  systemctl status "${SERVICE}" || true
  exit 1
fi
echo "service running: OK"

echo ""
echo "Full status:"
systemctl status "${SERVICE}" --no-pager || true
