# CrowdSec Nginx Auth Bouncer

A lightweight, in-memory Python bouncer for infrastructures using Nginx `auth_request`, Cloudflare, and Dockerized stacks (like Mailcow).

## How it works
1. **Nginx** extracts the real client IP from Cloudflare headers.
2. Nginx sends an internal `auth_request` to this bouncer.
3. The bouncer checks the IP against the **CrowdSec LAPI** in memory.
4. Returns `403 Forbidden` if the IP is banned, otherwise `200 OK`.

## Setup

### 1. Nginx Configuration
Add this inside your Nginx server block:

location = /crowdsec-check {
    internal;
    proxy_pass http://crowdsec-auth-bouncer:8080/;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Real-IP $remote_addr;
}

location / {
    auth_request /crowdsec-check;
    # your normal configuration...
}

### 2. Docker Compose Configuration
Add this to your `docker-compose.yml`:

services:
  crowdsec-auth-bouncer:
    image: python:3.11-slim
    container_name: crowdsec-auth-bouncer
    restart: always
    environment:
      - CROWDSEC_LAPI_URL=http://crowdsec:8080
      - CROWDSEC_API_KEY=your_api_key_here
    volumes:
      - ./bouncer.py:/app/bouncer.py:ro
    command: python3 /app/bouncer.py
    sysctls:
      - net.ipv4.ip_unprivileged_port_start=0

## License
MIT
