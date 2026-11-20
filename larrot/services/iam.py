"""IAM: Keystone APIs (projects, tokens)."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..core.envelopes import apigw_error
from ..core.jobs import new_request_id

router = APIRouter()


def _project_json(state, p):
    return {
        "domain_id": p["domain_id"],
        "is_domain": False,
        "parent_id": p["domain_id"],
        "name": p["name"],
        "description": "",
        "links": {"self": f"https://iam.myhuaweicloud.com/v3/projects/{p['id']}"},
        "id": p["id"],
        "enabled": True,
    }


@router.get("/v3/projects")
async def list_projects(request: Request):
    state = request.app.state.sim
    name = request.query_params.get("name")
    projects = [_project_json(state, p) for p in state.projects
                if not name or p["name"] == name]
    return {
        "projects": projects,
        "links": {
            "next": None, "previous": None,
            "self": "https://iam.myhuaweicloud.com/v3/projects",
        },
    }


@router.get("/v3/auth/projects")
async def list_auth_projects(request: Request):
    state = request.app.state.sim
    return {
        "projects": [_project_json(state, p) for p in state.projects],
        "links": {"self": "https://iam.myhuaweicloud.com/v3/auth/projects"},
    }


@router.post("/v3/auth/tokens")
async def create_token(request: Request):
    state = request.app.state.sim
    body = await request.json()

    methods = ((body.get("auth") or {}).get("identity") or {}).get("methods") or []
    if "password" not in methods:
        return JSONResponse(
            apigw_error("APIGW.0301", "Incorrect IAM authentication information: verify aksk signature fail"),
            status_code=401,
        )

    scope = ((body.get("auth") or {}).get("scope") or {})
    project_part = None
    if "project" in scope:
        proj = scope["project"]
        p = next((pr for pr in state.projects
                  if pr["name"] == proj.get("name") or pr["id"] == proj.get("id")), None)
        if p:
            project_part = {
                "id": p["id"], "name": p["name"],
                "domain": {"id": state.account["domain_id"], "name": state.account["name"]},
            }

    catalog = [
        {"id": f"{n}-svc", "type": t, "name": n,
         "endpoints": [{"id": f"{n}-ep", "region_id": "sim", "region": "sim",
                        "url": "http://127.0.0.1:8200", "interface": "public"}]}
        for t, n in [("identity", "iam"), ("compute", "ecs"), ("volumev2", "evs"),
                     ("network", "vpc"), ("image", "ims"), ("object-store", "obs")]
    ]

    import uuid
    token_body = {
        "token": {
            "catalog": catalog,
            "user": {"id": "iamuser-0001", "name": "simuser",
                     "domain": {"id": state.account["domain_id"], "name": state.account["name"]}},
            "roles": [],
            "project": project_part,
        }
    }
    response = JSONResponse(token_body, status_code=201)
    response.headers["X-Subject-Token"] = f"simtoken-{uuid.uuid4().hex}"
    return response
