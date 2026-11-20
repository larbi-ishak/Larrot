"""TMS: Tag Management Service: resource tags."""
from fastapi import APIRouter, Request
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v1.0/project-tags/create-or-delete")
async def create_or_delete_tags(request: Request):
    body = await request.json()
    return {"success": True, "request_id": new_id()}

@router.get("/v1.0/project-tags/resources")
@router.post("/v1.0/project-tags/resources")
async def list_tag_resources(request: Request):
    return {"resources": [], "total_count": 0}

@router.get("/v1.0/project-tags/tags")
async def list_tags(request: Request):
    return {"tags": [{"key": "env", "values": ["prod", "dev"]},
                      {"key": "team", "values": ["backend", "frontend"]}]}

@router.post("/v2.0/project-tags/resource-tags/action")
async def batch_tag_action(request: Request):
    body = await request.json()
    return {"success": True, "request_id": new_id()}
