#!/usr/bin/env python3
import os
import sys
import time
import requests
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

# Configuration via Environment Variables (CrowdSec Standard)
LAPI_URL = os.getenv("CROWDSEC_LAPI_URL", "http://localhost:8080").rstrip("/")
API_KEY = os.getenv("CROWDSEC_API_KEY", "")
SYNC_INTERVAL = int(os.getenv("CROWDSEC_SYNC_INTERVAL", "10"))
PORT = int(os.getenv("BOUNCER_PORT", "8080"))

if not API_KEY:
    print("[ERROR] CROWDSEC_API_KEY environment variable is required.", file=sys.stderr)
    sys.exit(1)

blocked_ips = set()

def sync_decisions():
    """Periodically fetches decisions from CrowdSec Local API"""
    global blocked_ips
    headers = {"X-Api-Key": API_KEY}
    while True:
        try:
            response = requests.get(f"{LAPI_URL}/v1/decisions", headers=headers, timeout=5)
            if response.status_code == 200:
                decisions = response.json()
                new_ips = set()
                if decisions:
                    for decision in decisions:
                        if decision.get("scope") == "Ip":
                            new_ips.add(decision.get("value"))
                blocked_ips = new_ips
        except Exception as e:
            print(f"[ERROR] Connection to CrowdSec LAPI failed: {e}", file=sys.stderr)
        time.sleep(SYNC_INTERVAL)

class BouncerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Read the real client IP forwarded by Nginx
        real_ip = self.headers.get("X-Real-IP")
        if not real_ip:
            self.send_response(200)
            self.end_headers()
            return

        if real_ip in blocked_ips:
            self.send_response(403) # Standard Reject Code
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress default logging to save disk space

def run():
    sync_thread = Thread(target=sync_decisions, daemon=True)
    sync_thread.start()
    print(f"[INFO] CrowdSec Auth Bouncer running on port {PORT}...")
    server = HTTPServer(('0.0.0.0', PORT), BouncerHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    run()
