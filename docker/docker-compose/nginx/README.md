# Nginx Reverse Proxy Deployment

This directory contains a production-ready Docker Compose setup for deploying Hindsight behind an Nginx reverse proxy with path-based routing (subpath deployment).

## Use Case

Deploy Hindsight under a subpath (e.g., `https://example.com/hindsight/`) instead of the root domain. This is useful when:
- Hosting multiple services under a single domain
- Using API gateways with path-based routing
- Running behind corporate proxies
- Multi-tenant deployments with path isolation

## Quick Start

### 1. Build the Docker Image

```bash
# From repo root
docker build -t hindsight:latest -f docker/standalone/Dockerfile .
```

### 2. Set Your LLM API Key

```bash
export OPENAI_API_KEY=your-key-here

# Or for other providers:
# export ANTHROPIC_API_KEY=your-key-here
```

### 3. Start the Stack

```bash
docker-compose -f docker/docker-compose/nginx/docker-compose.yml up
```

### 4. Verify

Access Hindsight at `http://localhost:8080/hindsight/`:

```bash
# API health check
curl http://localhost:8080/hindsight/health

# OpenAPI docs
open http://localhost:8080/hindsight/docs

# Control Plane UI
open http://localhost:8080/hindsight/
```

## Configuration Files

### `simple.conf`

Basic reverse proxy for API only. Use this when:
- You only need the API (headless deployment)
- Control Plane is hosted separately
- You're using a different UI

### `api-and-control-plane.conf`

Routes both API and Control Plane under the same base path. The router intelligently:
- Routes `/hindsight/v1/*`, `/hindsight/docs`, `/hindsight/health` to the API
- Routes `/hindsight/*` (UI pages) to the Control Plane
- Handles static assets (JS/CSS) correctly

### `docker-compose.yml`

Complete production-ready setup with:
- Hindsight API
- Hindsight Control Plane
- Nginx reverse proxy
- PostgreSQL database
- All configured with base path `/hindsight`

## Testing

Run the integration test to verify your setup:

```bash
./scripts/test-basepath.sh
```

This will:
1. Start API and Control Plane with base path
2. Start Nginx
3. Test all endpoints through the proxy
4. Clean up

## Troubleshooting

### 404 on API endpoints

**Problem:** API returns 404 for all requests

**Solution:** Ensure `HINDSIGHT_API_BASE_PATH` matches your Nginx location:
```bash
# If Nginx uses location /hindsight/
export HINDSIGHT_API_BASE_PATH=/hindsight
```

### Static assets fail to load (Control Plane)

**Problem:** Browser console shows 404 for CSS/JS files

**Solution:** Ensure both `basePath` and `assetPrefix` are set in `next.config.ts` and `NEXT_PUBLIC_BASE_PATH` is set before building:
```bash
export NEXT_PUBLIC_BASE_PATH=/hindsight
npm run build --workspace=hindsight-control-plane
```

### OpenAPI docs show wrong server URL

**Problem:** OpenAPI docs say "Server not found" or show wrong URL

**Solution:** The `root_path` parameter in FastAPI should match your base path. Check that `HINDSIGHT_API_BASE_PATH` is set.

### Nginx returns 502 Bad Gateway

**Problem:** Nginx can't reach upstream services

**Solution:** Check that API and Control Plane are running:
```bash
curl http://localhost:8888/hindsight/health  # API direct
curl http://localhost:3000/hindsight         # Control Plane direct
```

## Production Considerations

### HTTPS/TLS

Add SSL configuration to Nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # ... rest of config
}
```

### Security Headers

Add security headers to Nginx:

```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

### Rate Limiting

Protect your API from abuse:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /hindsight/ {
    limit_req zone=api burst=20 nodelay;
    # ... rest of config
}
```

### Monitoring

Enable access logs for monitoring:

```nginx
access_log /var/log/nginx/hindsight-access.log combined;
error_log /var/log/nginx/hindsight-error.log warn;
```

## Alternative Reverse Proxies

The same principles apply to other reverse proxies:

**Traefik:**
```yaml
http:
  routers:
    hindsight:
      rule: "PathPrefix(`/hindsight`)"
      service: hindsight

  services:
    hindsight:
      loadBalancer:
        servers:
          - url: "http://api:8888"
```

**Caddy:**
```caddyfile
example.com {
    handle /hindsight/* {
        reverse_proxy localhost:8888
    }
}
```

**HAProxy:**
```haproxy
backend hindsight
    server api localhost:8888
    reqrep ^([^\ :]*)\ /hindsight/(.*) \1\ /\2
```
