# Amazon Research Tool – how it runs

The app is run by **systemd** (not PM2) so it listens on **0.0.0.0:3000** and is reachable from the internet.

**Useful commands:**
- Status: `systemctl status amazon-tool`
- Restart: `systemctl restart amazon-tool`
- Logs: `journalctl -u amazon-tool -f`
- Stop: `systemctl stop amazon-tool`
- Start: `systemctl start amazon-tool`

The service is enabled to start on boot.
