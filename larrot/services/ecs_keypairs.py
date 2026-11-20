"""ECS Key Pairs: SSH key pair management."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
import base64, hashlib

router = APIRouter()


@router.post("/v2.1/{pid}/os-keypairs")
async def create_keypair(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ecs_keypairs"): s.ecs_keypairs = {}
    body = await request.json()
    kp_name = body.get("keypair", {}).get("name", f"key-{new_id()[:8]}")
    # Generate a fake SSH public key
    fake_pub = f"ssh-rsa {base64.b64encode(hashlib.sha256(kp_name.encode()).digest()).decode()} sim@larrot"
    kp_id = new_id()
    s.ecs_keypairs[kp_name] = {
        "name": kp_name, "public_key": fake_pub,
        "fingerprint": hashlib.md5(fake_pub.encode()).hexdigest(),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"keypair": {"name": kp_name, "public_key": fake_pub}}


@router.get("/v2.1/{pid}/os-keypairs")
async def list_keypairs(request: Request, pid: str):
    s = request.app.state.sim
    kps = [k for k in getattr(s, "ecs_keypairs", {}).values() if k["project_id"] == pid]
    return {"keypairs": [{"name": k["name"], "public_key": k["public_key"],
                           "fingerprint": k["fingerprint"]} for k in kps]}


@router.get("/v2.1/{pid}/os-keypairs/{keypair_name}")
async def show_keypair(request: Request, pid: str, keypair_name: str):
    s = request.app.state.sim
    kp = getattr(s, "ecs_keypairs", {}).get(keypair_name)
    if not kp or kp["project_id"] != pid:
        return JSONResponse({"error": {"code": "Ecs.0115", "message": "Keypair not found"}}, status_code=404)
    return {"keypair": {"name": kp["name"], "public_key": kp["public_key"], "fingerprint": kp["fingerprint"]}}


@router.delete("/v2.1/{pid}/os-keypairs/{keypair_name}")
async def delete_keypair(request: Request, pid: str, keypair_name: str):
    s = request.app.state.sim
    if keypair_name not in getattr(s, "ecs_keypairs", {}):
        return JSONResponse({"error": {"code": "Ecs.0115", "message": "Keypair not found"}}, status_code=404)
    del s.ecs_keypairs[keypair_name]
    return Response(status_code=204)


@router.post("/v2.1/{pid}/os-keypairs/import")
async def import_keypair(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ecs_keypairs"): s.ecs_keypairs = {}
    body = await request.json()
    kp_name = body.get("keypair", {}).get("name", f"imported-{new_id()[:8]}")
    pub_key = body.get("keypair", {}).get("public_key", "")
    s.ecs_keypairs[kp_name] = {
        "name": kp_name, "public_key": pub_key,
        "fingerprint": hashlib.md5(pub_key.encode()).hexdigest(),
        "created_at": now_millis(), "project_id": pid,
    }
    return {"keypair": {"name": kp_name, "public_key": pub_key}}
