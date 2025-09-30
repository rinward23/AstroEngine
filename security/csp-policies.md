# Content Security Policy

The AstroEngine UI and API endpoints enforce a restrictive CSP aligned with OWASP recommendations:

```
default-src 'self';
script-src 'self' 'nonce-{nonce}' https://www.googletagmanager.com;
style-src 'self' 'nonce-{nonce}' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: https://cdn.astroengine.com;
connect-src 'self' https://api.astroengine.com https://telemetry.astroengine.com;
frame-ancestors 'none';
object-src 'none';
base-uri 'self';
```

Tenants may register additional analytics endpoints through the security review process; updates must be versioned and deployed via Helm values.
