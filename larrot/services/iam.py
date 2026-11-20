"""IAM: Keystone APIs (projects, tokens)."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.envelopes import apigw_error
from ..core.jobs import new_request_id, new_id, now_millis

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


# ---------------------------------------------------------------------------
# users, groups, roles (tier-2 documented operations)
# ---------------------------------------------------------------------------

@router.post("/v3/users")
async def create_user(request: Request):
    state = request.app.state.sim
    if not hasattr(state, "iam_users"):
        state.iam_users = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse(apigw_error("IAM.0001", "name is required"), status_code=400)
    uid = new_id()
    state.iam_users[uid] = {
        "id": uid, "name": name, "domain_id": state.account["domain_id"],
        "enabled": body.get("enabled", True),
        "email": body.get("email", ""), "description": body.get("description", ""),
        "password_expires_at": None, "created_at": now_millis(),
    }
    return {"user": state.iam_users[uid]}


@router.get("/v3/users")
async def list_users(request: Request):
    state = request.app.state.sim
    users = list(getattr(state, "iam_users", {}).values())
    return {"users": users}


@router.get("/v3/users/{user_id}")
async def show_user(request: Request, user_id: str):
    state = request.app.state.sim
    u = getattr(state, "iam_users", {}).get(user_id)
    if not u:
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    return {"user": u}


@router.put("/v3/users/{user_id}")
async def update_user(request: Request, user_id: str):
    state = request.app.state.sim
    u = getattr(state, "iam_users", {}).get(user_id)
    if not u:
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    body = await request.json()
    for field in ("name", "email", "description", "enabled"):
        if field in body:
            u[field] = body[field]
    return {"user": u}


@router.delete("/v3/users/{user_id}")
async def delete_user(request: Request, user_id: str):
    state = request.app.state.sim
    if user_id not in getattr(state, "iam_users", {}):
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    del state.iam_users[user_id]
    return Response(status_code=204)


@router.post("/v3/groups")
async def create_user_group(request: Request):
    state = request.app.state.sim
    if not hasattr(state, "iam_groups"):
        state.iam_groups = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse(apigw_error("IAM.0001", "name is required"), status_code=400)
    gid = new_id()
    state.iam_groups[gid] = {
        "id": gid, "name": name, "domain_id": state.account["domain_id"],
        "description": body.get("description", ""), "created_at": now_millis(),
    }
    return {"group": state.iam_groups[gid]}


@router.get("/v3/groups")
async def list_user_groups(request: Request):
    state = request.app.state.sim
    return {"groups": list(getattr(state, "iam_groups", {}).values())}


@router.get("/v3/roles")
async def list_roles(request: Request):
    return {"roles": [
        {"id": "r_00000000000000000000000000000000", "name": "system_all_1",
         "description": "All permissions", "display_name": "Full access"},
        {"id": "r_00000000000000000000000000000001", "name": "te_admin_1",
         "description": "Tenant administrator", "display_name": "Tenant admin"},
    ]}


# ---------------------------------------------------------------------------
# role assignments and domains (tier-3 documented operations)
# ---------------------------------------------------------------------------

def _assignment_key(project_id, principal_type, principal_id, role_id):
    return f"{project_id}:{principal_type}:{principal_id}:{role_id}"


@router.put("/v3/projects/{project_id}/users/{user_id}/roles/{role_id}")
async def grant_user_role(request: Request, project_id: str, user_id: str, role_id: str):
    state = request.app.state.sim
    if not hasattr(state, "iam_role_assignments"):
        state.iam_role_assignments = {}
    state.iam_role_assignments[
        _assignment_key(project_id, "user", user_id, role_id)] = {
        "project_id": project_id, "principal_type": "user",
        "principal_id": user_id, "role_id": role_id}
    return Response(status_code=204)


@router.delete("/v3/projects/{project_id}/users/{user_id}/roles/{role_id}")
async def revoke_user_role(request: Request, project_id: str, user_id: str, role_id: str):
    state = request.app.state.sim
    key = _assignment_key(project_id, "user", user_id, role_id)
    if getattr(state, "iam_role_assignments", {}).pop(key, None) is None:
        return JSONResponse(apigw_error("IAM.0003", "role assignment not found"), status_code=404)
    return Response(status_code=204)


@router.get("/v3/projects/{project_id}/users/{user_id}/roles")
async def list_user_roles(request: Request, project_id: str, user_id: str):
    state = request.app.state.sim
    roles = [{"id": a["role_id"], "name": "assigned",
              "links": {"self": f"/v3/roles/{a['role_id']}"}}
             for a in getattr(state, "iam_role_assignments", {}).values()
             if a["project_id"] == project_id
             and a["principal_type"] == "user" and a["principal_id"] == user_id]
    return {"roles": roles}


@router.put("/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}")
async def grant_group_role(request: Request, project_id: str, group_id: str, role_id: str):
    state = request.app.state.sim
    if not hasattr(state, "iam_role_assignments"):
        state.iam_role_assignments = {}
    state.iam_role_assignments[
        _assignment_key(project_id, "group", group_id, role_id)] = {
        "project_id": project_id, "principal_type": "group",
        "principal_id": group_id, "role_id": role_id}
    return Response(status_code=204)


@router.delete("/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}")
async def revoke_group_role(request: Request, project_id: str, group_id: str, role_id: str):
    state = request.app.state.sim
    key = _assignment_key(project_id, "group", group_id, role_id)
    if getattr(state, "iam_role_assignments", {}).pop(key, None) is None:
        return JSONResponse(apigw_error("IAM.0003", "role assignment not found"), status_code=404)
    return Response(status_code=204)


@router.get("/v3/projects/{project_id}/groups/{group_id}/roles")
async def list_group_roles(request: Request, project_id: str, group_id: str):
    state = request.app.state.sim
    roles = [{"id": a["role_id"], "name": "assigned",
              "links": {"self": f"/v3/roles/{a['role_id']}"}}
             for a in getattr(state, "iam_role_assignments", {}).values()
             if a["project_id"] == project_id
             and a["principal_type"] == "group" and a["principal_id"] == group_id]
    return {"roles": roles}


@router.get("/v3/domains")
async def list_domains(request: Request):
    state = request.app.state.sim
    return {"domains": [{"id": state.account["domain_id"],
                          "name": state.account["name"],
                          "enabled": True, "description": "sim account"}]}
