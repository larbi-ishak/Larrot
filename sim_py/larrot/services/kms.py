"""KMS — key management service."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()


def _key_json(k):
    return {"key_id": k["id"], "domain_id": k["domain_id"], "key_alias": k["alias"],
            "key_description": k.get("description", ""), "realm": k.get("realm", "sim"),
            "key_spec": k.get("key_spec", "AES_256"), "key_usage": k.get("key_usage", "ENCRYPT_DECRYPT"),
            "key_state": k.get("state", "2"), "creation_date": k["created_at"],
            "scheduled_deletion_date": k.get("scheduled_deletion_date"),
            "enterprise_project_id": "0", "key_origin": "kms"}


@router.post("/v1/{pid}/kms/create-key")
async def create_key(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "kms_keys"):
        state.kms_keys = {}
    body = await request.json()
    key_id = new_id()
    now = now_millis()
    state.kms_keys[key_id] = {
        "id": key_id, "alias": body.get("key_alias", f"key-{key_id[:8]}"),
        "description": body.get("key_description", ""),
        "key_spec": body.get("key_spec", "AES_256"),
        "key_usage": body.get("key_usage", "ENCRYPT_DECRYPT"),
        "realm": body.get("realm", "sim"),
        "state": "2",  # 2 = enabled
        "created_at": now, "domain_id": state.account["domain_id"],
    }
    return {"key_id": key_id, "key_info": _key_json(state.kms_keys[key_id])}


@router.get("/v1/{pid}/kms/describe-key/{key_id}")
async def describe_key(request: Request, pid: str, key_id: str):
    state = request.app.state.sim
    if not hasattr(state, "kms_keys"):
        state.kms_keys = {}
    k = state.kms_keys.get(key_id)
    if not k:
        return JSONResponse({"error_msg": "Key not found", "error_code": "KMS.0101"}, status_code=404)
    return {"key_info": _key_json(k)}


@router.post("/v1/{pid}/kms/list-keys")
async def list_keys(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "kms_keys"):
        state.kms_keys = {}
    keys = [{"key_id": k["id"]} for k in state.kms_keys.values()]
    return {"keys": keys, "total": len(keys)}


@router.post("/v1/{pid}/kms/schedule-key-deletion")
async def schedule_key_deletion(request: Request, pid: str, key_id: str = None):
    state = request.app.state.sim
    body = await request.json()
    key_id = body.get("key_id")
    if not key_id or key_id not in state.kms_keys:
        return JSONResponse({"error_msg": "Key not found", "error_code": "KMS.0101"}, status_code=404)
    state.kms_keys[key_id]["state"] = "4"  # 4 = scheduled deletion
    return {"key_id": key_id}


@router.post("/v1/{pid}/kms/encrypt-data")
async def encrypt_data(request: Request, pid: str):
    """Encrypt data with a key — returns a fake cipher text blob."""
    state = request.app.state.sim
    body = await request.json()
    key_id = body.get("key_id")
    if not key_id or key_id not in getattr(state, "kms_keys", {}):
        return JSONResponse({"error_msg": "Key not found", "error_code": "KMS.0101"}, status_code=404)
    import base64
    plain = body.get("plain_text", "")
    cipher = base64.b64encode(f"ENCRYPTED:{plain}".encode()).decode()
    return {"cipher_text": cipher, "key_id": key_id}


@router.post("/v1/{pid}/kms/decrypt-data")
async def decrypt_data(request: Request, pid: str):
    """Decrypt data — reverses the fake encryption."""
    state = request.app.state.sim
    body = await request.json()
    key_id = body.get("key_id")
    if not key_id or key_id not in getattr(state, "kms_keys", {}):
        return JSONResponse({"error_msg": "Key not found", "error_code": "KMS.0101"}, status_code=404)
    import base64
    cipher = body.get("cipher_text", "")
    try:
        plain = base64.b64decode(cipher).decode()
        if plain.startswith("ENCRYPTED:"):
            plain = plain[10:]
    except Exception:
        plain = ""
    return {"plain_text": plain, "key_id": key_id}
