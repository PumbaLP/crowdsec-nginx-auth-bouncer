# CrowdSec Nginx Auth Bouncer
A lightweight, high-performance Python-based custom CrowdSec bouncer designed specifically for infrastructures utilizing **Nginx auth_request**, **Cloudflare proxying**, and **Mailcow (or similar Dockerized stacks)**.
It intercepts requests at the Nginx ingress level, validates the extracted X-Real-IP against the CrowdSec Local API (LAPI) in memory, and issues an immediate 403 Forbidden response if the client is banned—preventing unauthorized traffic from ever reaching your upstream applications.
## Features
 * **Zero Heavy Dependencies:** No need for Lua, OpenResty, or complex third-party Nginx modules.
 * **In-Memory Validation:** Ultra-low latency lookups (<1ms) using native Python sets.
 * **Cloudflare & IPv6 Ready:** Seamlessly works with forwarded real IP headers (both IPv4 and IPv6).
 * **Dockerized Architecture:** Easily integrates into existing setups.
## How It Works
 1. The client connects via **Cloudflare**, which attaches the original client IP to the request headers.
 2. **Nginx** extracts the true client IP using the real_ip module (CF-Connecting-IP or X-Forwarded-For).
 3. Nginx triggers an internal auth_request to this Bouncer before processing the actual request.
 4. The Bouncer evaluates the IP against its locally cached blacklist synchronized from the **CrowdSec LAPI**.
 5. If banned, Nginx drops the request with a 403 Forbidden response. Otherwise, access is granted.
## Setup & Installation
### 1. Nginx Configuration
Add the following block to your Nginx site configuration to handle the validation check:
```nginx
location /auth-request {
    internal;
    proxy_pass [http://127.0.0.1:8080/check](http://127.0.0.1:8080/check);
    proxy_pass_request_body off;
    proxy_set_header X-Original-URI $request_uri;
}

```
### 2. Standard Docker Setup
If you run a custom Docker stack:
 1. **Download the Script:**
   Place the bouncer.py file from this repository into your project directory next to your docker-compose.yml.
   ```bash
   wget [https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py](https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py)
   
   ```
 2. **Add the Service:**
   Add the following service configuration to your docker-compose.yml:
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
      - net.ipv4.ip_unprivileged_port_start=0

```
### 3. Mailcow Setup (docker-compose.override.yml)
For Mailcow installations, keep the configuration clean and separate.
 1. **Place the Script:**
   Download and save the bouncer.py file directly into Mailcow's Nginx configuration directory so the container can read it:
   ```bash
   # Run this inside your mailcow directory (e.g., /opt/mailcow-dockerized)
   wget -O ./data/conf/nginx/bouncer.py [https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py](https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py)
   
   ```
 2. **Override Configuration:**
   Leave your main docker-compose.yml untouched and put the service definition into your docker-compose.override.yml:
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
      - ./data/conf/nginx/bouncer.py:/app/bouncer.py:ro
    command: python3 /app/bouncer.py
    sysctls:
      - net.ipv4.ip_unprivileged_port_start=0
    networks:
      mailcow-net:
        ipv4_address: 172.22.1.250

```
### 4. Manual Installation (Alternative to Docker)
If you prefer running the bouncer directly on the host system without Docker:
 1. **Prerequisites:** Ensure Python 3.11+ is installed on your system.
 2. **File Placement:** Create a folder and download the script there:
   ```bash
   mkdir -p /usr/local/bin/crowdsec-bouncer
   wget -O /usr/local/bin/crowdsec-bouncer/bouncer.py [https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py](https://raw.githubusercontent.com/PumbaLP/crowdsec-nginx-auth-bouncer/main/bouncer.py)
   chmod +x /usr/local/bin/crowdsec-bouncer/bouncer.py
   
   ```
 3. **Create a Systemd Service:** Create a service file at /etc/systemd/system/crowdsec-bouncer.service:
```ini
[Unit]
Description=CrowdSec Nginx Auth Bouncer
After=network.target

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/crowdsec-bouncer/bouncer.py
Environment="CROWDSEC_LAPI_URL=http://localhost:8080"
Environment="CROWDSEC_API_KEY=YOUR_API_KEY"
Environment="BOUNCER_PORT=8080"
Restart=always
User=nobody

[Install]
WantedBy=multi-user.target

```
 4. **Enable and Start the service:**
```bash
systemctl daemon-reload
systemctl enable --now crowdsec-bouncer

```
## Troubleshooting
To verify that Nginx successfully routes traffic and passes correct IP formats to the bouncer, check the Nginx error logs.
