"""Gateway middleware: rate limit, chaos injection, signature verify, logging, journal."""

import asyncio
import logging
import time

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .core.signing import verify_sdk_hmac_sha256

logger = logging.getLogger("larrot")

# Paths that never require a signature, even in enforce mode: the local
# admin/UI surface, health/metrics, docs, and the password-based token
# endpoint (a client has no signature before it has credentials).
AUTH_EXEMPT_PREFIXES = (
    "/admin", "/console", "/docs", "/redoc", "/openapi.json",
    "/favicon.ico", "/metrics", "/health",
)
AUTH_EXEMPT_PATHS = {"/", "/v3/auth/tokens"}


def _needs_auth(path: str) -> bool:
    if path in AUTH_EXEMPT_PATHS:
        return False
    return not path.startswith(AUTH_EXEMPT_PREFIXES)


def _iam_error(check) -> JSONResponse:
    """Huawei's API gateway auth errors (api-sign-errorcode.html)."""
    if check.absent:
        # APIGW.0305: no credentials presented
        return JSONResponse(
            {"error_msg": "Incorrect authentication information.",
             "error_code": "APIGW.0305", "request_id": ""},
            status_code=401)
    if "unknown AK" in check.reason:
        msg = (f"Incorrect IAM authentication information: "
               f"Get secretKey failed,ak:{check.ak},err:ak not exist")
    else:
        msg = "Incorrect IAM authentication information: verify aksk signature fail"
    return JSONResponse(
        {"error_msg": msg, "error_code": "APIGW.0301", "request_id": ""},
        status_code=401)


async def gateway_middleware(request: Request, call_next) -> Response:
    """Applied to all REST routes. OBS has its own middleware."""
    state = request.app.state.sim
    _t0 = time.perf_counter()

    # Flatten headers for the verifier
    headers = [(k.lower(), v) for k, v in request.headers.items()]

    # --- Rate limiting (APIGW emulation, outermost layer) ---
    auth = next((v for k, v in headers if k == "authorization"), "")
    ak = ""
    if "Access=" in auth:
        ak = auth.split("Access=")[1].split(",")[0].strip()
    if not state.limiter.record(ak or "anonymous"):
        logger.warning("THROTTLED ak=%s", ak)
        status, body = state.limiter.error_response()
        return JSONResponse(body, status_code=status)

    # --- Chaos fault injection (ROADMAP 1.2) ---
    if getattr(state, "chaos", None) and state.chaos.rules:
        # clear any stale flag from a request that submitted no job
        state.chaos.consume_job_failure()
        injection = state.chaos.maybe_inject(request.method, request.url.path)
        if injection:
            status, body, latency_ms = injection
            logger.warning("CHAOS injected %s %s -> %s (rule %s)",
                           request.method, request.url.path, status,
                           body.get("chaos_rule_id"))
            if latency_ms:
                await asyncio.sleep(latency_ms / 1000)
            return JSONResponse(body, status_code=status)
        if request.method in ("POST", "PUT", "DELETE"):
            state.chaos.maybe_mark_job_failure(request.method, request.url.path)

    # --- Signature verification (accept-and-check) ---
    body = b""
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    check = verify_sdk_hmac_sha256(
        request.method,
        request.url.path,
        str(request.url.query) or None,
        headers,
        body,
        state.find_sk,
    )
    if check.absent:
        logger.info("%s %s (no signature)", request.method, request.url.path)
    elif check.valid:
        logger.info("%s %s signature OK (ak=%s)", request.method, request.url.path, check.ak)
    else:
        logger.warning("%s %s SIGNATURE INVALID ak=%s: %s",
                       request.method, request.url.path, check.ak, check.reason)

    # --- IAM enforcement (SIM_IAM=enforce) ---
    # accept (default): log mismatches, never reject - frictionless local dev.
    # enforce: reject unsigned/invalid requests with Huawei's real APIGW
    # errors, so clients can test their signing and credential handling.
    if getattr(state, "iam_mode", "accept") == "enforce" \
            and _needs_auth(request.url.path) and not check.valid:
        logger.warning("ENFORCE rejected %s %s (%s)",
                       request.method, request.url.path,
                       "no signature" if check.absent else check.reason)
        return _iam_error(check)

    response = await call_next(request)

    # --- Response identity + request journal ---
    duration_ms = (time.perf_counter() - _t0) * 1000
    from .core.jobs import new_request_id
    rid = request.headers.get("X-Request-Id") or new_request_id()
    response.headers["X-Request-Id"] = rid
    response.headers["x-larrot"] = request.app.version

    journal = getattr(state, "journal", None)
    if journal is not None and not request.url.path.startswith(
            ("/admin", "/health", "/metrics", "/docs", "/console",
             "/openapi", "/redoc", "/favicon")):
        journal.record(
            method=request.method, path=request.url.path,
            status=response.status_code, duration_ms=round(duration_ms, 1),
            request_id=rid,
            matched=response.status_code != 404,
            near_misses=getattr(request.state, "near_misses", []),
        )
    return response


async def obs_middleware(request: Request, call_next) -> Response:
    """OBS middleware: v2 signature verification (accept-and-check)."""
    from .core.signing import verify_obs_v2
    state = request.app.state.sim

    headers = [(k.lower(), v) for k, v in request.headers.items()]
    body = await request.body() if request.method in ("POST", "PUT") else b""

    check = verify_obs_v2(
        request.method,
        request.url.path,
        str(request.url.query) or None,
        headers,
        body,
        state.find_sk,
    )
    if check.valid:
        logger.info("%s %s OBS signature OK", request.method, request.url.path)
    elif not check.absent:
        logger.warning("%s %s OBS SIGNATURE INVALID: %s", request.method, request.url.path, check.reason)

    response = await call_next(request)
    response.headers["Server"] = "OBS"
    response.headers["x-obs-request-id"] = __import__("uuid").uuid4().hex.upper()
    return response
