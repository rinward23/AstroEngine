"""HTTP middleware helpers for FastAPI/Starlette applications."""

from __future__ import annotations

import zlib

from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.middleware.gzip import GZipMiddleware, IdentityResponder
from starlette.types import ASGIApp, Receive, Scope, Send


def _parse_accept_encoding(header: str) -> dict[str, float]:
    """Return mapping of encodings to their declared quality values."""

    encodings: dict[str, float] = {}
    for raw_token in header.split(","):
        token = raw_token.strip()
        if not token:
            continue
        parts = [part.strip() for part in token.split(";") if part.strip()]
        if not parts:
            continue
        name = parts[0].lower()
        q = 1.0
        for option in parts[1:]:
            if option.startswith("q="):
                try:
                    q = float(option[2:])
                except ValueError:
                    q = 0.0
        encodings[name] = q
    return encodings


def _encoding_quality(encodings: dict[str, float], name: str) -> float:
    """Look up the quality value for *name*, falling back to ``*`` if present."""

    name = name.lower()
    if name in encodings:
        return encodings[name]
    if "*" in encodings:
        return encodings["*"]
    return 0.0


class DeflateResponder(IdentityResponder):
    """Stream ``deflate`` compressed responses."""

    content_encoding = "deflate"

    def __init__(self, app: ASGIApp, minimum_size: int, compresslevel: int = 9) -> None:
        super().__init__(app, minimum_size)
        self._compressor = zlib.compressobj(level=compresslevel, wbits=-zlib.MAX_WBITS)

    def apply_compression(self, body: bytes, *, more_body: bool) -> bytes:  # noqa: D401 - base class docs
        chunk = self._compressor.compress(body)
        if not more_body:
            chunk += self._compressor.flush()
        return chunk


class DeflateMiddleware:
    """Serve ``deflate`` responses when clients explicitly request them."""

    def __init__(self, app: ASGIApp, minimum_size: int = 500, compresslevel: int = 9) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":  # pragma: no cover - delegated to Starlette
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        accept_encoding = headers.get("Accept-Encoding", "")
        encodings = _parse_accept_encoding(accept_encoding)
        gzip_q = _encoding_quality(encodings, "gzip")
        deflate_q = _encoding_quality(encodings, "deflate")

        if deflate_q > 0.0 and gzip_q <= 0.0:
            responder: ASGIApp = DeflateResponder(
                self.app, self.minimum_size, compresslevel=self.compresslevel
            )
        else:
            responder = IdentityResponder(self.app, self.minimum_size)

        await responder(scope, receive, send)


def configure_compression(
    app: FastAPI, *, minimum_size: int = 256, compresslevel: int = 6
) -> None:
    """Attach gzip and deflate compression middleware to *app*."""

    app.add_middleware(GZipMiddleware, minimum_size=minimum_size, compresslevel=compresslevel)
    app.add_middleware(
        DeflateMiddleware, minimum_size=minimum_size, compresslevel=compresslevel
    )


__all__ = [
    "configure_compression",
    "DeflateMiddleware",
]
