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

## Swiss ephemeris compliance note

AstroEngine’s application code is AGPL-3.0-only, but Swiss Ephemeris datasets are
governed by separate proprietary terms. Operators must opt in before distributing
or mounting that data. Use the documented CLI workflow (`astroengine-ephe
--agree-license --dest /opt/ephe`) only after confirming the upstream licence is
acceptable for your deployment and ensure `/opt/ephe` remains mounted read-only in
production containers.
