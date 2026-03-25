# If the app is not reachable from the browser

Two things were fixed on the server:

1. **Firewall:** Port **3000** is now allowed in UFW (it was previously blocked).
2. **Listen address:** The app already listens on **0.0.0.0** in `server.js`.

If the app still times out when you open **http://167.86.105.250:3000**, the PM2 process may have been started in an environment where it does not bind to the host network (e.g. Cursor SSH). Restart it from a **normal SSH session** so it binds correctly:

```bash
ssh root@167.86.105.250
cd /root/amazon-tool
pm2 delete amazon-tool 2>/dev/null
pm2 start server.js --name amazon-tool --interpreter node
pm2 save
ss -tlnp | grep 3000
```

You should see a line with `0.0.0.0:3000` and `node`. Then try **http://167.86.105.250:3000** in your browser again.
