# Amazon Research Tool – Server Setup Summary

## Completed on this server

- **Project directory:** `/root/amazon-tool`
- **System:** Packages updated
- **Installed:** git, curl, Node.js (v18.19.1), npm (9.2.0), PM2
- **Build tools:** build-essential (for native Node modules)

## Next step: deploy your local project

### Option A: Git (recommended)

1. **On your local machine:** Push your project to a Git remote (GitHub, GitLab, etc.).

2. **On this server:** Clone into the project directory:
   ```bash
   cd /root/amazon-tool
   git clone <your-repo-url> .
   ```
   (Use `.` to clone into the current folder so files land in `/root/amazon-tool`.)

3. **Install dependencies and build:**
   ```bash
   npm install
   npm run build
   ```

4. **Run with PM2:**
   ```bash
   pm2 start npm --name "amazon-tool" -- start
   pm2 save
   pm2 startup   # optional: run on server reboot
   ```

### Option B: rsync / SCP from your machine

From your **local** machine (not the server):

```bash
rsync -avz --exclude node_modules --exclude .next ./your-project/ user@your-vps-ip:/root/amazon-tool/
```

Then on the server:

```bash
cd /root/amazon-tool
npm install
npm run build
pm2 start npm --name "amazon-tool" -- start
```

### Option C: Upload via Cursor / SFTP

Upload your project files into `/root/amazon-tool`, then on the server:

```bash
cd /root/amazon-tool
npm install
npm run build
pm2 start npm --name "amazon-tool" -- start
```

---

## Useful commands

| Command | Purpose |
|--------|--------|
| `pm2 list` | List running apps |
| `pm2 logs amazon-tool` | View logs |
| `pm2 restart amazon-tool` | Restart the app |
| `pm2 stop amazon-tool` | Stop the app |

## Amazon Research platform (systemd service)

The Amazon research runtime runs as a systemd service for continuous operation.

- **Service file:** `deploy/amazon-research.service` (installed to `/etc/systemd/system/amazon-research.service`)
- **Install:** `sudo cp deploy/amazon-research.service /etc/systemd/system/` then:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable amazon-research
  sudo systemctl start amazon-research
  ```
  Or run: `sudo scripts/step182_install_systemd.sh`
- **Verify:** `systemctl status amazon-research` or `bash scripts/step182_systemd_verify.sh`
- **Expected:** service installed, service enabled, service running

## Environment variables

If your Next.js app needs env vars (e.g. API keys), create `/root/amazon-tool/.env.local` with your values before running `npm run build` and `pm2 start`.
