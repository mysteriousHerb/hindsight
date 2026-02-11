# Nginx Reverse Proxy Deployment

This directory contains a production-ready example for deploying Hindsight behind an Nginx reverse proxy with a custom base path (e.g., `/hindsight`).

## Quick Start (API-only, no rebuild)

Use the published Docker image for API reverse proxy:

```bash
docker-compose -f docker/docker-compose/nginx/docker-compose.yml up
```

**Access:**
- API docs: http://localhost:8080/hindsight/docs
- API health: http://localhost:8080/hindsight/health
- API endpoints: http://localhost:8080/hindsight/v1/...
- Control Plane (direct): http://localhost:9999

This works with the published image - no build required!

## Full Stack with Control Plane (requires build)

To deploy **both** API and Control Plane under `/hindsight`, you need to build locally with the base path configured:

### 1. Update docker-compose.yml

Uncomment the `build:` section and add `NEXT_PUBLIC_BASE_PATH` build arg:

```yaml
services:
  hindsight:
    build:
      context: ../../..
      dockerfile: docker/standalone/Dockerfile
      target: standalone
      args:
        NEXT_PUBLIC_BASE_PATH: /hindsight  # ← Add this
    image: ghcr.io/vectorize-io/hindsight:latest
    environment:
      HINDSIGHT_API_BASE_PATH: /hindsight
      NEXT_PUBLIC_BASE_PATH: /hindsight   # ← Add this
      # ... rest of environment
```

### 2. Update Dockerfile

Add the build arg in `docker/standalone/Dockerfile` (around line 108):

```dockerfile
# Copy built SDK directly into node_modules
COPY --from=sdk-builder /app/hindsight-clients/typescript ./node_modules/@vectorize-io/hindsight-client

# Accept base path as build argument (for reverse proxy deployments)
ARG NEXT_PUBLIC_BASE_PATH=""

# Build Control Plane
RUN npm exec -- next build
```

### 3. Update nginx.conf

Replace the nginx.conf content to handle both API and Control Plane:

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream hindsight_api {
        server hindsight:8888;
    }

    upstream hindsight_cp {
        server hindsight:9999;
    }

    server {
        listen 80;
        server_name _;

        # API endpoints
        location ~ ^/hindsight/(docs|openapi\.json|health|metrics|v1|mcp) {
            proxy_pass http://hindsight_api;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Next.js static files
        location ~ ^/hindsight/_next/ {
            proxy_pass http://hindsight_cp;
            proxy_set_header Host $http_host;
        }

        # Control Plane UI
        location /hindsight {
            proxy_pass http://hindsight_cp;
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location = / {
            return 301 /hindsight;
        }
    }
}
```

### 4. Build and Run

```bash
docker-compose -f docker/docker-compose/nginx/docker-compose.yml up --build
```

**Access:**
- API docs: http://localhost:8080/hindsight/docs
- Control Plane: http://localhost:8080/hindsight
- All under the same `/hindsight` path!

## Why Two Options?

**Option 1 (API-only)** is simpler and works with the published image because:
- The API accepts `HINDSIGHT_API_BASE_PATH` at runtime
- No rebuild needed

**Option 2 (Full stack)** requires a build because:
- Next.js `basePath` must be set at **build time** (not runtime)
- The published image wasn't built with a custom base path
- You need to rebuild with `NEXT_PUBLIC_BASE_PATH` build arg

## Configuration

### Environment Variables

**For API:**
- `HINDSIGHT_API_BASE_PATH` - API base path (e.g., `/hindsight`)
- `HINDSIGHT_API_LLM_PROVIDER` - LLM provider (default: `mock`)
- `OPENAI_API_KEY` - Your LLM API key (if not using mock)

**For Control Plane:**
- `NEXT_PUBLIC_BASE_PATH` - Control Plane base path (must match API base path)

### Nginx Configuration

The nginx config routes requests based on path:
- `/hindsight/docs`, `/hindsight/v1/*`, etc. → API (port 8888)
- `/hindsight/_next/*` → Control Plane static assets (port 9999)
- `/hindsight/*` → Control Plane pages (port 9999)

## Production Considerations

### HTTPS/TLS

Add SSL configuration to nginx:

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # ... rest of config
}
```

### Rate Limiting

Protect your API:

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /hindsight/v1/ {
    limit_req zone=api burst=20 nodelay;
    # ... rest of config
}
```

### External PostgreSQL

For production, use external PostgreSQL instead of embedded pg0:

```yaml
services:
  postgres:
    image: ankane/pgvector:latest
    environment:
      POSTGRES_DB: hindsight
      POSTGRES_USER: hindsight
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  hindsight:
    environment:
      HINDSIGHT_API_DATABASE_URL: postgresql://hindsight:${POSTGRES_PASSWORD}@postgres:5432/hindsight
```

## Troubleshooting

### API returns 404

**Problem:** API endpoints return 404

**Solution:** Ensure `HINDSIGHT_API_BASE_PATH` matches nginx location:
```bash
# If nginx uses /hindsight/
export HINDSIGHT_API_BASE_PATH=/hindsight
```

### Control Plane assets fail to load

**Problem:** Browser shows 404 for JS/CSS files

**Solution:** Make sure you built with `NEXT_PUBLIC_BASE_PATH`:
```bash
docker-compose up --build  # Don't forget --build!
```

### Nginx 502 Bad Gateway

**Problem:** Nginx can't reach services

**Solution:** Check containers are healthy:
```bash
docker-compose ps
docker-compose logs hindsight
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
          - url: "http://hindsight:8888"
```

**Caddy:**
```caddyfile
example.com {
    handle /hindsight/* {
        reverse_proxy hindsight:8888
    }
}
```

## Learn More

- [Hindsight Documentation](https://github.com/vectorize-io/hindsight/tree/main/hindsight-docs)
- [Next.js basePath](https://nextjs.org/docs/app/api-reference/config/next-config-js/basePath)
- [Nginx Reverse Proxy](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
