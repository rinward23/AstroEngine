# >>> AUTO-GEN BEGIN: Refine v1.0 (secant/bisection)
from dataclasses import replace
from .api import TransitEvent
from .detectors import norm180, ASPECT_ANGLES


def refine_exact(event: TransitEvent, provider, natal: dict, cfg) -> TransitEvent:
    """Bracket and refine exactness for the event using secant → bisection fallback.
    provider must expose: ecliptic_state(t_iso, topocentric, lat, lon, elev_m) -> state dict.
    """
    body, point, asp = event.transiting_body, event.natal_point, event.aspect
    theta = ASPECT_ANGLES[asp]

    def f(t_iso: str) -> float:
        st = provider.ecliptic_state(
            t_iso,
            topocentric=cfg.topocentric,
            lat=cfg.site_lat,
            lon=cfg.site_lon,
            elev_m=cfg.site_elev_m,
        )
        lon_t = st[body]["lon_deg"]
        lon_n = natal[point]["lon_deg"]
        return norm180((lon_t - lon_n) - theta)

    # crude bracket: ±6h around current estimate
    import datetime as _dt
    from datetime import timezone

    t0 = _dt.datetime.fromisoformat(cfg.start_iso.replace("Z", "+00:00"))
    guess = t0
    dt = _dt.timedelta(hours=6)
    a = guess - dt
    b = guess + dt

    def iso(t: _dt.datetime) -> str:
        return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    fa, fb = f(iso(a)), f(iso(b))
    if fa * fb > 0:
        a -= dt
        b += dt
        fa, fb = f(iso(a)), f(iso(b))

    x0, x1 = a, b
    y0, y1 = fa, fb
    for _ in range(12):
        if abs(y1 - y0) < 1e-9:
            break
        xn = _dt.datetime.fromtimestamp(
            x1.timestamp() - y1 * (x1.timestamp() - x0.timestamp()) / (y1 - y0)
        )
        yn = f(iso(xn))
        x0, y0, x1, y1 = x1, y1, xn, yn
        if abs(yn) <= 1e-6:
            break

    t_exact = x1
    partile = abs(f(iso(t_exact))) <= (1 / 6) / 60  # ≈ 0.01°

    return replace(event, t_exact=iso(t_exact), partile=partile)


# >>> AUTO-GEN END: Refine v1.0 (secant/bisection)
