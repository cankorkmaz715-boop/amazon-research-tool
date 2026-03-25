# Upload local project to this VPS (no GitHub)

Your project **amazon-research-tool** is on your local machine. This server only has this guide. Use one of the methods below to transfer files, then run the "After upload" steps on the VPS.

---

## Step 1: Find your local project folder

On your **local machine** (not the server), your project is somewhere like:

- **Windows:** `C:\Users\YourName\...\amazon-research-tool` or similar
- **Mac/Linux:** `~/amazon-research-tool` or `~/projects/amazon-research-tool` or similar

In Cursor, if you have the project open, the path is in the left sidebar (root folder name) or in **File → Open Folder**. You can also open a **local** terminal in that folder and run `pwd` to see the full path.

---

## Step 2: Safest ways to transfer (local → VPS)

### Method A: Cursor drag‑and‑drop (simplest)

1. In Cursor, connect to the VPS via **Remote-SSH** (you’re already there if you see this server’s files).
2. Open a **second Cursor window** (or Explorer) and open your **local** `amazon-research-tool` folder.
3. In the **local** window, select all project files (e.g. `package.json`, `src`, `app`, `next.config.js`, etc.).  
   **Exclude:** `node_modules`, `.next`, `.git` (optional).
4. Drag the selection into the VPS Explorer panel, into the folder **`/root/amazon-tool`** (or the `amazon-tool` folder you see in the remote view).
5. Wait until the upload finishes.

**Why it’s safe:** Uses your existing SSH connection, no extra tools, and you choose exactly what to copy.

---

### Method B: SCP from your local terminal (one command)

On your **local** machine, open a terminal in your project folder (e.g. `cd amazon-research-tool`), then run:

```bash
# Replace:
#   /path/to/amazon-research-tool  → your actual local path
#   root@YOUR_VPS_IP               → your SSH user and server (e.g. root@1.2.3.4)

scp -r . root@YOUR_VPS_IP:/root/amazon-tool/
```

To **exclude** `node_modules` and `.next` (recommended), use `rsync` instead:

```bash
rsync -avz --exclude 'node_modules' --exclude '.next' --exclude '.git' ./ root@YOUR_VPS_IP:/root/amazon-tool/
```

**Why it’s safe:** Uses the same SSH key/password as Cursor; traffic is encrypted.

---

### Method C: Zip locally, then SCP the zip

1. **Locally**, in your project folder, create an archive (exclude `node_modules`, `.next`):

   **Mac/Linux:**
   ```bash
   zip -r amazon-tool.zip . -x 'node_modules/*' -x '.next/*' -x '.git/*'
   ```

   **Windows (PowerShell):**
   ```powershell
   Compress-Archive -Path * -DestinationPath amazon-tool.zip
   ```
   (Then remove `node_modules` and `.next` from the zip if they were included.)

2. Upload the zip:
   ```bash
   scp amazon-tool.zip root@YOUR_VPS_IP:/root/amazon-tool/
   ```

3. **On the VPS** (in SSH/Cursor terminal):
   ```bash
   cd /root/amazon-tool && unzip -o amazon-tool.zip && rm amazon-tool.zip
   ```

---

## Step 3: After upload – run on the VPS

In a terminal **on the VPS** (Cursor’s SSH terminal or your SSH session), run:

```bash
cd /root/amazon-tool
ls -la
npm install
npm run build
pm2 start npm --name "amazon-tool" -- start
pm2 save
pm2 list
```

This verifies files, installs dependencies, builds, and starts the app with PM2.
