"""IAM: Keystone APIs (projects, tokens)."""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.envelopes import apigw_error
from ..core.jobs import new_id, now_millis

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
    """List the projects of the domain: the per-region resource containers."""
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
    """List the projects the current token can access (the SDK discovery endpoint)."""
    state = request.app.state.sim
    return {
        "projects": [_project_json(state, p) for p in state.projects],
        "links": {"self": "https://iam.myhuaweicloud.com/v3/auth/projects"},
    }


@router.post("/v3/auth/tokens")
async def create_token(request: Request):
    """Issue a token: exchange username/password (or another auth method) for an X-Subject-Token."""
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
    """Create an IAM user: the login identity with a password and access keys."""
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
    """List the IAM users of the domain."""
    state = request.app.state.sim
    users = list(getattr(state, "iam_users", {}).values())
    return {"users": users}


@router.get("/v3/users/{user_id}")
async def show_user(request: Request, user_id: str):
    """Show one user: name, status, and email."""
    state = request.app.state.sim
    u = getattr(state, "iam_users", {}).get(user_id)
    if not u:
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    return {"user": u}


@router.put("/v3/users/{user_id}")
async def update_user(request: Request, user_id: str):
    """Update a user's name, email, or password."""
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
    """Delete an IAM user."""
    state = request.app.state.sim
    if user_id not in getattr(state, "iam_users", {}):
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    del state.iam_users[user_id]
    return Response(status_code=204)


@router.post("/v3/groups")
async def create_user_group(request: Request):
    """Create a user group."""
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
    """List user groups: the containers that carry permissions."""
    state = request.app.state.sim
    return {"groups": list(getattr(state, "iam_groups", {}).values())}


@router.get("/v3/roles")
async def list_roles(request: Request):
    """List roles: the permission sets that can be granted."""
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
    """Grant a role to a user on a project: the actual permission assignment."""
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
    """Revoke a role from a user on a project."""
    state = request.app.state.sim
    key = _assignment_key(project_id, "user", user_id, role_id)
    if getattr(state, "iam_role_assignments", {}).pop(key, None) is None:
        return JSONResponse(apigw_error("IAM.0003", "role assignment not found"), status_code=404)
    return Response(status_code=204)


@router.get("/v3/projects/{project_id}/users/{user_id}/roles")
async def list_user_roles(request: Request, project_id: str, user_id: str):
    """List the roles a user has on a project."""
    state = request.app.state.sim
    roles = [{"id": a["role_id"], "name": "assigned",
              "links": {"self": f"/v3/roles/{a['role_id']}"}}
             for a in getattr(state, "iam_role_assignments", {}).values()
             if a["project_id"] == project_id
             and a["principal_type"] == "user" and a["principal_id"] == user_id]
    return {"roles": roles}


@router.put("/v3/projects/{project_id}/groups/{group_id}/roles/{role_id}")
async def grant_group_role(request: Request, project_id: str, group_id: str, role_id: str):
    """Grant a role to a group on a project."""
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
    """Revoke a role from a group on a project."""
    state = request.app.state.sim
    key = _assignment_key(project_id, "group", group_id, role_id)
    if getattr(state, "iam_role_assignments", {}).pop(key, None) is None:
        return JSONResponse(apigw_error("IAM.0003", "role assignment not found"), status_code=404)
    return Response(status_code=204)


@router.get("/v3/projects/{project_id}/groups/{group_id}/roles")
async def list_group_roles(request: Request, project_id: str, group_id: str):
    """List the roles a group has on a project."""
    state = request.app.state.sim
    roles = [{"id": a["role_id"], "name": "assigned",
              "links": {"self": f"/v3/roles/{a['role_id']}"}}
             for a in getattr(state, "iam_role_assignments", {}).values()
             if a["project_id"] == project_id
             and a["principal_type"] == "group" and a["principal_id"] == group_id]
    return {"roles": roles}


@router.get("/v3/domains")
async def list_domains(request: Request):
    """List domains (accounts)."""
    state = request.app.state.sim
    return {"domains": [{"id": state.account["domain_id"],
                          "name": state.account["name"],
                          "enabled": True, "description": "sim account"}]}


# ---------------------------------------------------------------------------
# agencies, project details, group membership, catalog (tier-4)
# ---------------------------------------------------------------------------

@router.post("/v3.0/OS-AGENCY/agencies")
async def create_agency(request: Request):
    """Create an agency: the delegated identity that lets another account or service act as you."""
    state = request.app.state.sim
    if not hasattr(state, "iam_agencies"):
        state.iam_agencies = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse(apigw_error("IAM.0001", "name is required"), status_code=400)
    aid = new_id()
    state.iam_agencies[aid] = {
        "id": aid, "name": name,
        "domain_id": state.account["domain_id"],
        "delegated_domain_id": body.get("delegated_domain_id", ""),
        "duration": body.get("duration", "FOREVER"),
        "description": body.get("description", ""),
        "create_time": now_millis(),
    }
    return {"agency": state.iam_agencies[aid]}


@router.get("/v3.0/OS-AGENCY/agencies")
async def list_agencies(request: Request):
    """List agencies."""
    state = request.app.state.sim
    return {"agencies": list(getattr(state, "iam_agencies", {}).values())}


@router.get("/v3.0/OS-AGENCY/agencies/{agency_id}")
async def show_agency(request: Request, agency_id: str):
    """Show one agency: its delegated domain and trust duration."""
    state = request.app.state.sim
    a = getattr(state, "iam_agencies", {}).get(agency_id)
    if not a:
        return JSONResponse(apigw_error("IAM.0004", "agency not found"), status_code=404)
    return {"agency": a}


@router.put("/v3.0/OS-AGENCY/agencies/{agency_id}")
async def update_agency(request: Request, agency_id: str):
    """Update an agency's trust policy or duration."""
    state = request.app.state.sim
    a = getattr(state, "iam_agencies", {}).get(agency_id)
    if not a:
        return JSONResponse(apigw_error("IAM.0004", "agency not found"), status_code=404)
    body = await request.json()
    for field in ("description", "duration"):
        if field in body:
            a[field] = body[field]
    return {"agency": a}


@router.delete("/v3.0/OS-AGENCY/agencies/{agency_id}")
async def delete_agency(request: Request, agency_id: str):
    """Delete an agency."""
    state = request.app.state.sim
    if agency_id not in getattr(state, "iam_agencies", {}):
        return JSONResponse(apigw_error("IAM.0004", "agency not found"), status_code=404)
    del state.iam_agencies[agency_id]
    return Response(status_code=204)


@router.get("/v3/projects/{project_id}")
async def show_project(request: Request, project_id: str):
    """Show one project: its name, domain, and status."""
    state = request.app.state.sim
    p = state.project(project_id)
    if not p:
        return JSONResponse(apigw_error("IAM.0005", "project not found"), status_code=404)
    return {"project": {"id": p["id"], "name": p["name"],
                          "domain_id": p["domain_id"], "enabled": True}}


@router.put("/v3/projects/{project_id}")
async def update_project(request: Request, project_id: str):
    """Update a project's name or description."""
    state = request.app.state.sim
    p = state.project(project_id)
    if not p:
        return JSONResponse(apigw_error("IAM.0005", "project not found"), status_code=404)
    body = await request.json()
    if "description" in body:
        p["description"] = body["description"]
    return {"project": {"id": p["id"], "name": p["name"],
                          "domain_id": p["domain_id"], "enabled": True}}


@router.put("/v3/groups/{group_id}/users/{user_id}")
async def add_user_to_group(request: Request, group_id: str, user_id: str):
    """Add a user to a group: the user inherits the group's roles."""
    state = request.app.state.sim
    g = getattr(state, "iam_groups", {}).get(group_id)
    u = getattr(state, "iam_users", {}).get(user_id)
    if not g or not u:
        return JSONResponse(apigw_error("IAM.0006", "group or user not found"), status_code=404)
    members = g.setdefault("users", [])
    if user_id not in members:
        members.append(user_id)
    return Response(status_code=204)


@router.delete("/v3/groups/{group_id}/users/{user_id}")
async def remove_user_from_group(request: Request, group_id: str, user_id: str):
    """Remove a user from a group."""
    state = request.app.state.sim
    g = getattr(state, "iam_groups", {}).get(group_id)
    if not g:
        return JSONResponse(apigw_error("IAM.0006", "group not found"), status_code=404)
    if user_id not in g.get("users", []):
        return JSONResponse(apigw_error("IAM.0007", "user not in group"), status_code=404)
    g["users"] = [x for x in g["users"] if x != user_id]
    return Response(status_code=204)


@router.get("/v3/groups/{group_id}/users")
async def list_group_users(request: Request, group_id: str):
    """List the users in a group."""
    state = request.app.state.sim
    g = getattr(state, "iam_groups", {}).get(group_id)
    if not g:
        return JSONResponse(apigw_error("IAM.0006", "group not found"), status_code=404)
    users = [state.iam_users[uid] for uid in g.get("users", [])
             if uid in getattr(state, "iam_users", {})]
    return {"users": users}


@router.get("/v3/users/{user_id}/groups")
async def list_user_groups_for_user(request: Request, user_id: str):
    """List the groups a user belongs to."""
    state = request.app.state.sim
    if user_id not in getattr(state, "iam_users", {}):
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    groups = [g for g in getattr(state, "iam_groups", {}).values()
              if user_id in g.get("users", [])]
    return {"groups": groups}


@router.get("/v3/auth/catalog")
async def get_service_catalog(request: Request):
    """Show the service catalog: every service's endpoints (SDK discovery)."""
    return {"catalog": [
        {"id": "sim-ecs", "name": "ecs", "type": "compute",
         "endpoints": [{"id": "sim-ecs-ep", "interface": "public",
                         "region": "ap-southeast-1",
                         "url": "http://127.0.0.1:8200"}]},
        {"id": "sim-evs", "name": "evs", "type": "volumev2",
         "endpoints": [{"id": "sim-evs-ep", "interface": "public",
                         "region": "ap-southeast-1",
                         "url": "http://127.0.0.1:8200"}]},
        {"id": "sim-obs", "name": "obs", "type": "object-store",
         "endpoints": [{"id": "sim-obs-ep", "interface": "public",
                         "region": "ap-southeast-1",
                         "url": "http://127.0.0.1:8201"}]},
    ]}


# ---------------------------------------------------------------------------
# identity providers and token lifecycle (tier-5)
# ---------------------------------------------------------------------------

@router.put("/v3.0/OS-FEDERATION/identity_providers")
async def create_identity_provider(request: Request):
    """Register an identity provider: the federation IdP (OIDC or SAML)."""
    state = request.app.state.sim
    if not hasattr(state, "iam_idps"):
        state.iam_idps = {}
    body = await request.json()
    pid_ = body.get("id", "")
    if not pid_:
        return JSONResponse(apigw_error("IAM.0001", "id is required"), status_code=400)
    if pid_ in state.iam_idps:
        return JSONResponse(apigw_error("IAM.0008", "identity provider already exists"),
                            status_code=409)
    state.iam_idps[pid_] = {
        "id": pid_, "enabled": body.get("enabled", False),
        "description": body.get("description", ""),
        "domain_id": state.account["domain_id"],
        "links": {"self": f"/v3.0/OS-FEDERATION/identity_providers/{pid_}"},
    }
    return JSONResponse({"identity_provider": state.iam_idps[pid_]}, status_code=201)


@router.get("/v3.0/OS-FEDERATION/identity_providers")
async def list_identity_providers(request: Request):
    """List registered identity providers."""
    state = request.app.state.sim
    return {"identity_providers": list(getattr(state, "iam_idps", {}).values())}


@router.get("/v3.0/OS-FEDERATION/identity_providers/{provider_id}")
async def show_identity_provider(request: Request, provider_id: str):
    """Show one identity provider: its protocol and status."""
    state = request.app.state.sim
    p = getattr(state, "iam_idps", {}).get(provider_id)
    if not p:
        return JSONResponse(apigw_error("IAM.0009", "identity provider not found"),
                            status_code=404)
    return {"identity_provider": p}


@router.delete("/v3.0/OS-FEDERATION/identity_providers/{provider_id}")
async def delete_identity_provider(request: Request, provider_id: str):
    """Delete an identity provider."""
    state = request.app.state.sim
    if provider_id not in getattr(state, "iam_idps", {}):
        return JSONResponse(apigw_error("IAM.0009", "identity provider not found"),
                            status_code=404)
    del state.iam_idps[provider_id]
    return Response(status_code=204)


@router.head("/v3/auth/tokens")
async def validate_token(request: Request):
    """Verify a token: HEAD with X-Subject-Token (sim always accepts)."""
    token = request.headers.get("x-subject-token", "")
    if not token:
        return JSONResponse(apigw_error("IAM.0010", "X-Subject-Token is required"),
                            status_code=401)
    return Response(status_code=200, headers={"X-Subject-Token": token})


@router.delete("/v3/auth/tokens")
async def revoke_token(request: Request):
    """Revoke a token (logout). The sim accepts any token."""
    token = request.headers.get("x-subject-token", "")
    if not token:
        return JSONResponse(apigw_error("IAM.0010", "X-Subject-Token is required"),
                            status_code=401)
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# federation mappings and protocols (tier-6)
# ---------------------------------------------------------------------------

@router.put("/v3.0/OS-FEDERATION/mappings")
async def create_mapping(request: Request):
    """Create a mapping: the rules converting IdP assertions to local identities."""
    state = request.app.state.sim
    if not hasattr(state, "iam_mappings"):
        state.iam_mappings = {}
    body = await request.json()
    mid = body.get("id", "")
    if not mid:
        return JSONResponse(apigw_error("IAM.0001", "id is required"), status_code=400)
    if mid in state.iam_mappings:
        return JSONResponse(apigw_error("IAM.0011", "mapping already exists"), status_code=409)
    state.iam_mappings[mid] = {
        "id": mid, "rules": body.get("rules", []),
        "links": {"self": f"/v3.0/OS-FEDERATION/mappings/{mid}"},
    }
    return JSONResponse({"mapping": state.iam_mappings[mid]}, status_code=201)


@router.get("/v3.0/OS-FEDERATION/mappings")
async def list_mappings(request: Request):
    """List mappings."""
    state = request.app.state.sim
    return {"mappings": list(getattr(state, "iam_mappings", {}).values())}


@router.get("/v3.0/OS-FEDERATION/mappings/{mapping_id}")
async def show_mapping(request: Request, mapping_id: str):
    """Show one mapping's rules."""
    state = request.app.state.sim
    m = getattr(state, "iam_mappings", {}).get(mapping_id)
    if not m:
        return JSONResponse(apigw_error("IAM.0012", "mapping not found"), status_code=404)
    return {"mapping": m}


@router.delete("/v3.0/OS-FEDERATION/mappings/{mapping_id}")
async def delete_mapping(request: Request, mapping_id: str):
    """Delete a mapping."""
    state = request.app.state.sim
    if mapping_id not in getattr(state, "iam_mappings", {}):
        return JSONResponse(apigw_error("IAM.0012", "mapping not found"), status_code=404)
    del state.iam_mappings[mapping_id]
    return Response(status_code=204)


@router.put("/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}")
async def create_protocol(request: Request, provider_id: str, protocol_id: str):
    """Configure a provider's protocol: how federation assertions map to local users."""
    state = request.app.state.sim
    idp = getattr(state, "iam_idps", {}).get(provider_id)
    if not idp:
        return JSONResponse(apigw_error("IAM.0009", "identity provider not found"),
                            status_code=404)
    if not hasattr(state, "iam_protocols"):
        state.iam_protocols = {}
    key = f"{provider_id}/{protocol_id}"
    if key in state.iam_protocols:
        return JSONResponse(apigw_error("IAM.0013", "protocol already exists"), status_code=409)
    body = await request.json()
    state.iam_protocols[key] = {
        "id": protocol_id, "provider_id": provider_id,
        "mapping_id": body.get("mapping_id", ""),
        "links": {"self": f"/v3.0/OS-FEDERATION/identity_providers/"
                           f"{provider_id}/protocols/{protocol_id}"},
    }
    return JSONResponse({"protocol": state.iam_protocols[key]}, status_code=201)


@router.get("/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols")
async def list_protocols(request: Request, provider_id: str):
    """List a provider's protocols."""
    state = request.app.state.sim
    if provider_id not in getattr(state, "iam_idps", {}):
        return JSONResponse(apigw_error("IAM.0009", "identity provider not found"),
                            status_code=404)
    protos = [p for p in getattr(state, "iam_protocols", {}).values()
              if p["provider_id"] == provider_id]
    return {"protocols": protos}


@router.get("/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}")
async def show_protocol(request: Request, provider_id: str, protocol_id: str):
    """Show one protocol."""
    state = request.app.state.sim
    p = getattr(state, "iam_protocols", {}).get(f"{provider_id}/{protocol_id}")
    if not p:
        return JSONResponse(apigw_error("IAM.0014", "protocol not found"), status_code=404)
    return {"protocol": p}


@router.delete("/v3.0/OS-FEDERATION/identity_providers/{provider_id}/protocols/{protocol_id}")
async def delete_protocol(request: Request, provider_id: str, protocol_id: str):
    """Delete a protocol."""
    state = request.app.state.sim
    key = f"{provider_id}/{protocol_id}"
    if key not in getattr(state, "iam_protocols", {}):
        return JSONResponse(apigw_error("IAM.0014", "protocol not found"), status_code=404)
    del state.iam_protocols[key]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# access keys (OS-CREDENTIAL, tier-7)
# ---------------------------------------------------------------------------

@router.post("/v3.0/OS-CREDENTIAL/credentials")
async def create_access_key(request: Request):
    """Create an access key (AK/SK) for a user: the permanent API credentials."""
    state = request.app.state.sim
    if not hasattr(state, "iam_credentials"):
        state.iam_credentials = {}
    body = await request.json()
    user_id = body.get("user_id", "")
    if user_id and user_id not in getattr(state, "iam_users", {}):
        return JSONResponse(apigw_error("IAM.0002", "user not found"), status_code=404)
    ak = "HWY" + new_id()[:17].upper()
    sk = new_id().replace("-", "") + new_id().replace("-", "")  # 64 chars
    state.iam_credentials[ak] = {
        "access": ak, "secret": sk, "status": "active",
        "user_id": user_id, "description": body.get("description", ""),
        "create_time": now_millis(),
    }
    return {"credential": {"access": ak, "secret": sk, "status": "active",
                            "user_id": user_id,
                            "description": body.get("description", "")}}


@router.get("/v3.0/OS-CREDENTIAL/credentials")
async def list_access_keys(request: Request):
    """List a user's access keys with their status."""
    state = request.app.state.sim
    creds = [{"access": c["access"], "status": c["status"],
              "user_id": c["user_id"], "description": c["description"],
              "create_time": c["create_time"]}
             for c in getattr(state, "iam_credentials", {}).values()]
    return {"credentials": creds}


@router.get("/v3.0/OS-CREDENTIAL/credentials/{access_key}")
async def show_access_key(request: Request, access_key: str):
    """Show one access key: its creation time and last use."""
    state = request.app.state.sim
    c = getattr(state, "iam_credentials", {}).get(access_key)
    if not c:
        return JSONResponse(apigw_error("IAM.0015", "access key not found"), status_code=404)
    return {"credential": {"access": c["access"], "status": c["status"],
                            "user_id": c["user_id"], "description": c["description"],
                            "create_time": c["create_time"]}}


@router.delete("/v3.0/OS-CREDENTIAL/credentials/{access_key}")
async def delete_access_key(request: Request, access_key: str):
    """Delete an access key."""
    state = request.app.state.sim
    if access_key not in getattr(state, "iam_credentials", {}):
        return JSONResponse(apigw_error("IAM.0015", "access key not found"), status_code=404)
    del state.iam_credentials[access_key]
    return Response(status_code=204)
