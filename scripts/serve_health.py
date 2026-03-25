#!/usr/bin/env python3
"""Optional minimal health endpoint. Serves GET /health with JSON. Run: python scripts/serve_health.py."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def get_health():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db
    init_db()
    from amazon_research.monitoring import health_check
    return health_check()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health" or self.path == "/health/":
            try:
                body = get_health()
                data = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(503)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("HEALTH_PORT", "8765"))
    with HTTPServer(("0.0.0.0", port), HealthHandler) as httpd:
        print(f"Health endpoint http://0.0.0.0:{port}/health")
        httpd.serve_forever()
