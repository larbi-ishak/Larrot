"""SDK-HMAC-SHA256 and OBS v2 signing: verification (server) and signing (client).

Two signing universes (EMPIRICAL_SPEC §1.4):
- REST services: SDK-HMAC-SHA256 (HMAC-SHA256, canonical request)
- OBS: v2 HMAC-SHA1 (different StringToSign, unsigned list params)
"""

import hashlib
import hmac
import base64
import time
import urllib.parse
from dataclasses import dataclass, field

ALGORITHM = "SDK-HMAC-SHA256"
EMPTY_PAYLOAD_HASH = hashlib.sha256(b"").hexdigest()

# OBS v2 signed sub-resources (API_DOCS_RESEARCH §1.2): list params NOT included
OBS_SIGNED_SUBRESOURCES = {
    "acl", "delete", "lifecycle", "location", "logging", "notification",
    "partNumber", "policy", "requestPayment", "torrent", "uploadId", "uploads",
    "versionId", "versioning", "versions", "website", "storageinfo", "quota",
    "tagging", "cors", "restore", "replication",
}


@dataclass
class SignatureCheck:
    """Result of a signature verification (informational: accept-and-check)."""
    ak: str = ""
    valid: bool = False
    reason: str = ""
    absent: bool = False


# ---------------------------------------------------------------------------
# SDK-HMAC-SHA256: server-side verification
# ---------------------------------------------------------------------------

def _canonical_uri(path: str) -> str:
    """Canonical URI: must end with '/' for signing (trailing slash added)."""
    return path if path.endswith("/") else path + "/"


def _canonical_query(query: str | None) -> str:
    """Canonical query: RFC3986-encoded, sorted by key."""
    if not query:
        return ""
    pairs = []
    for part in query.split("&"):
        if not part:
            continue
        k, _, v = part.partition("=")
        pairs.append((k, v))
    pairs.sort()
    return "&".join(f"{k}={v}" if v else k for k, v in pairs)


def _canonical_headers(signed: list[str], headers: list[tuple[str, str]]) -> str:
    """Canonical headers block: 'name:value\\n' per signed header."""
    out = ""
    for name in signed:
        vals = [v.strip() for k, v in headers if k.lower() == name]
        out += f"{name}:{','.join(vals)}\n"
    return out


def verify_sdk_hmac_sha256(
    method: str,
    path: str,
    query: str | None,
    headers: list[tuple[str, str]],
    body: bytes,
    sk_lookup,
) -> SignatureCheck:
    """Verify an incoming SDK-HMAC-SHA256 signature (accept-and-check)."""
    auth = next((v for k, v in headers if k.lower() == "authorization"), None)
    if not auth:
        return SignatureCheck(absent=True, reason="no Authorization header")

    if auth.startswith("OBS "):
        return SignatureCheck(absent=True, reason="OBS v2 signature (checked by OBS layer)")

    if not auth.startswith(ALGORITHM):
        return SignatureCheck(reason=f"unsupported scheme: {auth[:30]}")

    # Parse: "SDK-HMAC-SHA256 Access=AK, SignedHeaders=a;b;c, Signature=hex"
    rest = auth[len(ALGORITHM):].strip()
    ak, signed_headers_str, presented_sig = "", "", ""
    for part in rest.split(", "):
        if part.startswith("Access="):
            ak = part[7:].strip()
        elif part.startswith("SignedHeaders="):
            signed_headers_str = part[14:].strip()
        elif part.startswith("Signature="):
            presented_sig = part[10:].strip()

    if not all([ak, signed_headers_str, presented_sig]):
        return SignatureCheck(ak=ak, reason="malformed Authorization header")

    x_sdk_date = next((v.strip() for k, v in headers if k.lower() == "x-sdk-date"), "")
    if not x_sdk_date:
        return SignatureCheck(ak=ak, reason="missing X-Sdk-Date header")

    signed = signed_headers_str.split(";")
    payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_PAYLOAD_HASH

    canonical_request = "\n".join([
        method.upper(),
        _canonical_uri(path),
        _canonical_query(query),
        _canonical_headers(signed, headers),
        signed_headers_str,
        payload_hash,
    ])

    string_to_sign = "\n".join([
        ALGORITHM,
        x_sdk_date,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    sk = sk_lookup(ak)
    if sk is None:
        return SignatureCheck(ak=ak, reason=f"unknown AK '{ak}'")

    expected = hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    valid = hmac.compare_digest(expected, presented_sig)
    return SignatureCheck(
        ak=ak, valid=valid,
        reason="signature OK" if valid else f"mismatch: expected {expected[:16]}… got {presented_sig[:16]}…",
    )


# ---------------------------------------------------------------------------
# SDK-HMAC-SHA256: client-side signing (for hcli)
# ---------------------------------------------------------------------------

def sign_sdk_request(
    method: str, path: str, query: str | None,
    host: str, body: bytes, ak: str, sk: str,
) -> dict[str, str]:
    """Sign a REST request: returns the headers to add."""
    date = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    payload_hash = hashlib.sha256(body).hexdigest() if body else EMPTY_PAYLOAD_HASH

    canonical_headers = f"content-type:application/json\nhost:{host}\nx-sdk-date:{date}\n"
    signed_headers = "content-type;host;x-sdk-date"

    canonical_request = "\n".join([
        method.upper(),
        _canonical_uri(path),
        _canonical_query(query),
        canonical_headers,
        signed_headers,
        payload_hash,
    ])

    string_to_sign = "\n".join([
        ALGORITHM, date,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    signature = hmac.new(sk.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    return {
        "X-Sdk-Date": date,
        "Authorization": f"{ALGORITHM} Access={ak}, SignedHeaders={signed_headers}, Signature={signature}",
    }


# ---------------------------------------------------------------------------
# OBS v2: server-side verification
# ---------------------------------------------------------------------------

def _obs_canonical_resource(bucket: str | None, path: str, query: str | None) -> str:
    """CanonicalizedResource: /bucket/key + signed sub-resources only."""
    res = path  # path already contains /bucket/key
    if query:
        subs = sorted(p for p in query.split("&") if p.split("=")[0] in OBS_SIGNED_SUBRESOURCES)
        if subs:
            res += "?" + "&".join(subs)
    return res


def verify_obs_v2(
    method: str,
    path: str,
    query: str | None,
    headers: list[tuple[str, str]],
    body: bytes,
    sk_lookup,
) -> SignatureCheck:
    """Verify an OBS v2 HMAC-SHA1 signature (accept-and-check)."""
    auth = next((v for k, v in headers if k.lower() == "authorization"), "")
    if not auth.startswith("OBS "):
        return SignatureCheck(absent=True, reason="not an OBS Authorization")

    rest = auth[4:]
    ak, _, presented = rest.partition(":")
    ak, presented = ak.strip(), presented.strip()
    if not ak or not presented:
        return SignatureCheck(reason="malformed OBS Authorization")

    sk = sk_lookup(ak)
    if sk is None:
        return SignatureCheck(ak=ak, reason=f"unknown AK '{ak}'")

    def get(name):
        return ",".join(v.strip() for k, v in headers if k.lower() == name)

    content_md5 = get("content-md5")
    content_type = get("content-type")
    # Date is EMPTY in StringToSign when x-obs-date is present
    date = "" if any(k.lower() == "x-obs-date" for k, _ in headers) else get("date")

    # Canonicalized headers: sorted x-obs-* headers
    xobs = {}
    for k, v in headers:
        if k.lower().startswith("x-obs-"):
            key = k.lower()
            if key in xobs:
                xobs[key] += "," + v.strip()
            else:
                xobs[key] = v.strip()

    sts = f"{method.upper()}\n{content_md5}\n{content_type}\n{date}\n"
    for k in sorted(xobs):
        sts += f"{k}:{xobs[k]}\n"
    sts += _obs_canonical_resource(None, path, query)

    expected = base64.b64encode(hmac.new(sk.encode(), sts.encode(), hashlib.sha1).digest()).decode()
    valid = hmac.compare_digest(expected, presented)
    return SignatureCheck(
        ak=ak, valid=valid,
        reason="signature OK" if valid else f"mismatch: expected {expected[:12]}… got {presented[:12]}…",
    )


# ---------------------------------------------------------------------------
# OBS v2: client-side signing
# ---------------------------------------------------------------------------

def sign_obs_request(
    method: str, bucket: str, key: str, query: str | None,
    host: str, body: bytes, content_type: str, ak: str, sk: str,
) -> dict[str, str]:
    """Sign an OBS request: returns the headers to add."""
    date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())

    resource = f"/{bucket}" if bucket else "/"
    if key:
        resource += f"/{key}"
    if query:
        subs = sorted(p for p in query.split("&") if p.split("=")[0] in OBS_SIGNED_SUBRESOURCES)
        if subs:
            resource += "?" + "&".join(subs)

    sts = f"{method.upper()}\n\n{content_type}\n{date}\n{resource}"
    sig = base64.b64encode(hmac.new(sk.encode(), sts.encode(), hashlib.sha1).digest()).decode()
    return {
        "Date": date,
        "Authorization": f"OBS {ak}:{sig}",
    }
