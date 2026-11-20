"""KMS: key management service."""

from fastapi import APIRouter, Request
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
    """Encrypt data with a key: returns a fake cipher text blob."""
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
    """Decrypt data: reverses the fake encryption."""
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


@router.post("/v1/{pid}/kms/enable-key")
async def enable_key(request: Request, pid: str):
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}}, status_code=404)
    k["state"] = "2"  # 2 = enabled
    k["updated_at"] = now_millis()
    return {"key_id": k["id"], "key_state": 2}


@router.post("/v1/{pid}/kms/disable-key")
async def disable_key(request: Request, pid: str):
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}}, status_code=404)
    k["state"] = "3"  # 3 = disabled
    k["updated_at"] = now_millis()
    return {"key_id": k["id"], "key_state": 3}


@router.post("/v1/{pid}/kms/gen-random")
async def gen_random(request: Request, pid: str):
    import base64
    import os as _os
    body = await request.json()
    length = body.get("random_data_length", 64)
    if not isinstance(length, int) or not (16 <= length <= 8192):
        return JSONResponse({"error": {"code": "KMS.1001",
                                        "message": "random_data_length must be 16-8192"}}, status_code=400)
    return {"random_data": base64.b64encode(_os.urandom(length)).decode()}


@router.get("/v1/{pid}/kms/get-publickey/{key_id}")
async def get_public_key(request: Request, pid: str, key_id: str):
    s = request.app.state.sim
    k = getattr(s, "kms_keys", {}).get(key_id)
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}}, status_code=404)
    return {"key_id": k["id"], "public_key":
            "-----BEGIN PUBLIC KEY-----\nU2ltLVB1YmxpY0tleQ==\n-----END PUBLIC KEY-----\n"}


@router.post("/v1/{pid}/kms/update-key-alias")
async def update_key_alias(request: Request, pid: str):
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}},
                            status_code=404)
    alias = body.get("key_alias", "")
    if not alias:
        return JSONResponse({"error": {"code": "KMS.1001",
                                        "message": "key_alias is required"}}, status_code=400)
    k["alias"] = alias
    k["updated_at"] = now_millis()
    return {"key_id": k["id"], "key_alias": alias}


@router.post("/v1/{pid}/kms/create-datakey")
async def create_data_key(request: Request, pid: str):
    """Generate a data key (returns plain + encrypted data key)."""
    import base64 as _b64
    import os as _os
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}},
                            status_code=404)
    if k.get("state", "2") != "2":
        return JSONResponse({"error": {"code": "KMS.1002",
                                        "message": "key is disabled, operation failed"}},
                            status_code=400)
    key_spec = body.get("datakey_length", 256)
    plain = _b64.b64encode(_os.urandom(key_spec // 8)).decode()
    cipher = _b64.b64encode(f"sim-encrypted:{plain}".encode()).decode()
    return {"data_key_length": key_spec, "plain_text": plain,
            "cipher_text": cipher, "key_id": k["id"]}


@router.post("/v1/{pid}/kms/encrypt-datakey")
async def encrypt_data_key(request: Request, pid: str):
    """Encrypt a plain data key with a CMK."""
    import base64 as _b64
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}},
                            status_code=404)
    plain = body.get("plain_text", "")
    if not plain:
        return JSONResponse({"error": {"code": "KMS.1001",
                                        "message": "plain_text is required"}}, status_code=400)
    cipher = _b64.b64encode(f"sim-encrypted:{plain}".encode()).decode()
    return {"key_id": k["id"], "cipher_text": cipher}


@router.post("/v1/{pid}/kms/decrypt-datakey")
async def decrypt_data_key(request: Request, pid: str):
    """Decrypt an encrypted data key."""
    import base64 as _b64
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}},
                            status_code=404)
    cipher = body.get("cipher_text", "")
    if not cipher:
        return JSONResponse({"error": {"code": "KMS.1001",
                                        "message": "cipher_text is required"}}, status_code=400)
    try:
        raw = _b64.b64decode(cipher).decode()
        if not raw.startswith("sim-encrypted:"):
            raise ValueError("not a sim cipher")
        plain = raw[len("sim-encrypted:"):]
    except Exception:
        return JSONResponse({"error": {"code": "KMS.1003",
                                        "message": "invalid cipher_text"}}, status_code=400)
    return {"key_id": k["id"], "plain_text": plain}


@router.post("/v1/{pid}/kms/cancel-key-deletion")
async def cancel_key_deletion(request: Request, pid: str):
    """Cancel the scheduled deletion of a CMK (restores it to disabled)."""
    s = request.app.state.sim
    body = await request.json()
    k = getattr(s, "kms_keys", {}).get(body.get("key_id", ""))
    if not k:
        return JSONResponse({"error": {"code": "KMS.0101", "message": "key not found"}},
                            status_code=404)
    k["state"] = "3"  # disabled (pending deletion cancelled)
    k.pop("deletion_date", None)
    k["updated_at"] = now_millis()
    return {"key_id": k["id"], "key_state": 3}
