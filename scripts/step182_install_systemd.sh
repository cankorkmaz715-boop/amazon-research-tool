#!/usr/bin/env bash
# Step 182: Install Amazon Research as a systemd service.
# Run with: sudo scripts/step182_install_systemd.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SERVICE_FILE="${PROJECT_ROOT}/deploy/amazon-research.service"
DEST="/etc/systemd/system/amazon-research.service"

if [[ ! -f "${SERVICE_FILE}" ]]; then
  echo "Error: ${SERVICE_FILE} not found."
  exit 1
fi

cp "${SERVICE_FILE}" "${DEST}"
echo "Installed ${DEST}"

systemctl daemon-reload
systemctl enable amazon-research
systemctl start amazon-research

echo "Done. Check with: systemctl status amazon-research"
