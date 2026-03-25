# Recurring Execution (Cron / Systemd)

The pipeline (discovery → refresh → scoring) can run on a schedule using **cron** or **systemd**. Safe default: **once per day at 2:00 AM**.

## Entrypoint

- **Script:** `scripts/run_scheduler_once.py`
- **Module:** `python -m amazon_research.run_scheduler_once` (from repo root with `PYTHONPATH=src` or run from project root)

Both run the pipeline once and exit (exit code 0 on full success, 1 if a stage failed).

## Option A: Cron

1. **Enable:** Edit crontab: `crontab -e`
   - Add one line (adjust paths to your install):
   ```text
   0 2 * * * cd /root/amazon-tool && /root/amazon-tool/.venv/bin/python scripts/run_scheduler_once.py >> /var/log/amazon-research-cron.log 2>&1
   ```
   - See `config/cron.example` for more examples.

2. **Disable:** Remove or comment out that line in crontab.

3. **Verify:** After 2:00 AM, check `/var/log/amazon-research-cron.log` or run manually: `cd /root/amazon-tool && .venv/bin/python scripts/run_scheduler_once.py`

## Option B: Systemd timer

1. **Enable:**
   - Copy examples and adjust paths/user:
     ```bash
     sudo cp config/amazon-research.service.example /etc/systemd/system/amazon-research.service
     sudo cp config/amazon-research.timer.example /etc/systemd/system/amazon-research.timer
     # Edit both files and set correct WorkingDirectory, User, paths, and EnvironmentFile
     ```
   - Reload and enable the timer:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl enable amazon-research.timer
     sudo systemctl start amazon-research.timer
     ```

2. **Disable:**
   ```bash
   sudo systemctl stop amazon-research.timer
   sudo systemctl disable amazon-research.timer
   ```

3. **Verify:** `sudo systemctl list-timers amazon-research.timer` or run once: `sudo systemctl start amazon-research.service` then `journalctl -u amazon-research.service -n 50`

## Rollback

- **Cron:** Remove the crontab line; no further runs.
- **Systemd:** Stop and disable the timer (commands above); optionally remove the unit files from `/etc/systemd/system/`.

## Frequency

Default is **once per day** at 2:00 AM. Do not set a higher frequency without considering proxy/rate limits and anti-bot risk.
