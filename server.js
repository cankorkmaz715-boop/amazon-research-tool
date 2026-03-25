/**
 * Minimal server for Amazon Research Tool.
 * Uses DATABASE_URL from .env and serves a simple status page.
 */
require('dotenv').config();
const http = require('http');
const { Client } = require('pg');

const PORT = process.env.PORT || 3000;

async function handleRequest(req, res) {
  if (req.url !== '/' && req.url !== '/health') {
    res.writeHead(404);
    res.end('Not found');
    return;
  }

  let dbStatus = 'unknown';
  try {
    const client = new Client({ connectionString: process.env.DATABASE_URL });
    await client.connect();
    const result = await client.query('SELECT current_database(), current_user');
    await client.end();
    dbStatus = `connected (db: ${result.rows[0].current_database}, user: ${result.rows[0].current_user})`;
  } catch (err) {
    dbStatus = `error: ${err.message}`;
  }

  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(
    `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Amazon Research Tool</title></head><body>` +
    `<h1>Amazon Research Tool</h1><p>Server is running.</p>` +
    `<p><strong>PostgreSQL:</strong> ${dbStatus}</p>` +
    `</body></html>`
  );
}

const server = http.createServer(handleRequest);
server.listen(PORT, '0.0.0.0', () => {
  console.log(`Amazon Research Tool listening on http://0.0.0.0:${PORT}`);
});
