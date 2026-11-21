"""Near-miss route diagnostics: when a request matches no route, suggest the closest ones.

The WireMock pattern, adapted: with hundreds of operations, a misspelled
or wrong-version SDK URL should fail with an actionable error, not a
bare 404. Distance = 1 - similarity (lower is closer); a matching HTTP
method is a strong signal.
"""

import difflib

METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}
# Never suggest these to a client that hit an unknown service path.
EXCLUDED_PREFIXES = ("/admin", "/docs", "/redoc", "/openapi", "/favicon",
                    "/metrics", "/health", "/console")
EXCLUDED_EXACT = {"/"}


def _walk(routes):
    """Yield actual API routes, transparently through FastAPI's
    _IncludedRouter wrappers (0.165+) and older flat layouts."""
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None and getattr(inner, "routes", None):
            yield from _walk(inner.routes)
        else:
            yield route


def candidate_routes(app) -> list[tuple[str, str]]:
    """All public (method, path) pairs the simulator serves."""
    out = []
    for route in _walk(app.routes):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if not methods or not path or path.startswith(EXCLUDED_PREFIXES):
            continue
        if path in EXCLUDED_EXACT:
            continue
        for m in methods:
            if m in METHODS:
                out.append((m, path))
    return out


def near_misses(app, method: str, path: str, limit: int = 3) -> list[dict]:
    """The closest registered routes to (method, path), best first."""
    scored = []
    for m, p in candidate_routes(app):
        ratio = difflib.SequenceMatcher(None, path, p).ratio()
        if m == method.upper():
            ratio = min(1.0, ratio + 0.15)
        scored.append({"method": m, "path": p,
                       "distance": round(1.0 - ratio, 3)})
    scored.sort(key=lambda x: x["distance"])
    return scored[:limit]
