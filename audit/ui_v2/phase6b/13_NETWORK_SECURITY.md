# AUDIT REPORT — PHASE 6B: NETWORK ISOLATION & SECURITY HEADERS

## 1. Localhost Isolation Verification
Socket inspection on VPS (`ss -lntp`):
- `127.0.0.1:50051`: Execution Service (LISTEN, process `python` pid 276477).
- `127.0.0.1:8088`: Web Origin (LISTEN, process `python` pid 276524).
- `0.0.0.0:50051`: Absent.
- `0.0.0.0:8088`: Absent.
- Neither port is exposed to the public Internet. All external traffic terminates at Cloudflare and Nginx reverse proxy.

## 2. Cloudflare Edge Proxy & Public Routing
- Domain: `https://trader.noza.site`
- Edge CDN: Cloudflare
- Cloudflare configuration modifications: **0** (existing configuration preserved).

## 3. HTTP Security Header Enforcement
Queried directly on `https://trader.noza.site/`:
- `Content-Security-Policy`:
  `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://unpkg.com https://telegram.org; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:; img-src 'self' data: https:; connect-src 'self' https:; frame-ancestors 'self' https://web.telegram.org https://*.telegram.org`
- `Strict-Transport-Security`: `max-age=31536000; includeSubDomains`
- `X-Content-Type-Options`: `nosniff`
- `X-Frame-Options`: `SAMEORIGIN`
- `Referrer-Policy`: `strict-origin-when-cross-origin`
- `Permissions-Policy`: `camera=(), microphone=(), geolocation=()`

## 4. File Permission ACLs
- Authoritative runtime directory: `/opt/trader-stack/.runtime/`
  - Permissions: `0700` (`drwx------`), owner `trader:trader`.
- Runtime environment secrets: `/opt/trader-stack/.runtime/trader-stack.env`
  - Permissions: `0600` (`-rw-------`), owner `trader:trader`.
- World-readable runtime secrets: **0**.
