# CrowdSec Nginx Auth Bouncer
A lightweight, high-performance Python-based custom CrowdSec bouncer designed specifically for infrastructures utilizing **Nginx auth_request**, **Cloudflare proxying**, and **Mailcow (or similar Dockerized stacks)**.
It intercepts requests at the Nginx ingress level, validates the extracted X-Real-IP against the CrowdSec Local API (LAPI) in memory, and issues an immediate 403 Forbidden response if the client is banned—preventing unauthorized traffic from ever reaching your upstream applications.
## Features
 * **Zero Heavy Dependencies:** No need for Lua, OpenResty, or complex third-party Nginx modules.
 * **In-Memory Validation:** Ultra-low latency lookups (<1ms) using native Python sets.
 * **Cloudflare & IPv6 Ready:** Seamlessly works with forwarded real IP headers (both IPv4 and IPv6).
 * **Dockerized Architecture:** Easily integrates into existing docker-compose setups like Mailcow.
## How It Works
 1. The client connects via **Cloudflare**, which attaches the original client IP to the request headers.
 2. **Nginx** extracts the true client IP using the real_ip module (CF-Connecting-IP or X-Forwarded-For).
 3. Nginx triggers an internal auth_request to this Bouncer before processing the actual request.
 4. The Bouncer evaluates the IP against its locally cached blacklist synchronized from the **CrowdSec LAPI**.
 5. If banned, Nginx drops the request with a 403 Forbidden response. Otherwise, access is granted.
## Setup
### 1. Nginx Configuration
Add the following block to your Nginx virtual host configuration (e.g., inside Mailcow's site configs or reverse proxy setup):
```nginx
# Endpoint for CrowdSec verification
location = /crowdsec-check {
    internal;
    proxy_pass http://crowdsec-auth-bouncer:8080/; # Point to the Bouncer container port
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    
    # Crucial: Pass the extracted real client IP to the bouncer
    proxy_set_header X-Real-IP $remote_addr;
}

# Protect your location blocks
location / {
    auth_request /crowdsec-check;
    
    # Your normal proxy/upstream configuration here
    # proxy_pass http://my_upstream;
}

```
### 2. Docker Compose Configuration
Generate a generic API key using the CrowdSec CLI on your host:
```bash
cscli bouncers add mailcow-auth-bouncer

```
Add or append this service to your docker-compose.yml (or docker-compose.override.yml for Mailcow):
```yaml
services:
  crowdsec-auth-bouncer:
    image: python:3.11-slim
    container_name: crowdsec-auth-bouncer
    restart: always
    environment:
      - CROWDSEC_LAPI_URL=http://crowdsec:8080
      - CROWDSEC_API_KEY=YOUR_GENERATED_API_KEY_HERE
      - CROWDSEC_SYNC_INTERVAL=10
      - BOUNCER_PORT=8080
    volumes:
      - ./bouncer.py:/app/bouncer.py:ro
    command: python3 /app/bouncer.py
    sysctls:
      # Fix for dual-stack IPv4/IPv6 DNS resolution inside custom Docker bridges
      - net.ipv4.ip_unprivileged_port_start=0

```
## Troubleshooting
To verify that Nginx successfully routes traffic and passes correct IP formats to the bouncer, inspect the live container logs:
```bash
docker compose logs -f crowdsec-auth-bouncer

```
A healthy synchronization process logs the following on startup:
```text
[CROWDSEC] Initial sync successful. Loaded 112412 IPs.
[INFO] Starting CrowdSec Auth Bouncer on port 8080...

```
## License
MIT License. Feel free to use, modify, and distribute.
