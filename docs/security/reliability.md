# Security and Reliability Controls

AstroEngine services expose natal, composite, and transit data sourced from
SolarFire-compatible datasets. To protect tenant data and ensure deterministic
outputs, production deployments must apply the following controls.

## HTTP headers and CORS

- `SecurityHeadersMiddleware` injects `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, and `Permissions-Policy` on every response. When TLS
  terminates before the application and `RELATIONSHIP_ENABLE_HSTS=1`, the
  middleware also sets `Strict-Transport-Security` with the configured
  `RELATIONSHIP_HSTS_MAX_AGE`.
- CORS is configured with explicit allowlists. Origins, methods, and headers are
  parsed from environment variables (`CORS_ALLOW_ORIGINS`, `CORS_ALLOW_METHODS`,
  `CORS_ALLOW_HEADERS`) and fall back to a minimal `GET/POST/OPTIONS` surface.
  No wildcard access is permitted outside development builds.

## Rate limiting

- The relationship API uses a token bucket per client IP. Tokens are stored in
  Redis via an atomic Lua script when Redis is available, with an in-process
  fallback for offline development. Headers `X-RateLimit-*` communicate the
  quota, while `429` responses include `X-RateLimit-Reason: token_bucket` and a
  `Retry-After` that reflects the time until the next token.

## Request sizing and disconnect resilience

- `BodyLimitMiddleware` caps request bodies by inspecting `Content-Length` and
  short-circuiting oversize payloads before they reach business logic. Client
  disconnects are detected and logged so abandoned computations do not get
  misclassified as server faults. Uvicorn is launched with an explicit
  `timeout_keep_alive` (default 10s, override via `UVICORN_TIMEOUT_KEEP_ALIVE`)
  to prevent idle sockets from accumulating.
- Timeline-style endpoints must continue to enforce their existing window caps
  (see `app/schemas/*` window validators) so a single request cannot request an
  unbounded sweep.

## Secrets, configuration, and dependency hygiene

- All service configuration is derived from Pydantic settings backed by
  environment variables and optional `.env` files; secrets are never baked into
  container images.
- CI should run `pip-audit` (or `safety`) and treat critical vulnerabilities as
  hard failures so compromised dependencies never reach production.
