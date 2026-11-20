"""Gateway middleware: rate limit, chaos injection, signature verify, logging."""

import asyncio
import logging

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from .core.signing import verify_sdk_hmac_sha256

logger = logging.getLogger("larrot")


async def gateway_middleware(request: Request, call_next) -> Response:
    """Applied to all REST routes. OBS has its own middleware."""
    state = request.app.state.sim

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

    response = await call_next(request)
    response.headers["X-Request-Id"] = request.headers.get("X-Request-Id", "")
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
