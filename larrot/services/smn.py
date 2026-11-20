"""SMN: Simple Message Notification: topics, subscriptions."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v2/{pid}/notifications/topics")
async def create_topic(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "smn_topics"): s.smn_topics = {}
    body = await request.json()
    tid = new_id()
    s.smn_topics[tid] = {"id": tid, "name": body.get("name", f"topic-{tid[:8]}"),
        "display_name": body.get("display_name", ""), "subscriptions": [],
        "created_at": now_millis(), "project_id": pid,
        "topic_urn": f"urn:smn:sim:{pid}:{body.get('name', 'topic')}"}
    return {"topic_urn": s.smn_topics[tid]["topic_urn"], "request_id": new_id()}

@router.get("/v2/{pid}/notifications/topics")
async def list_topics(request: Request, pid: str):
    s = request.app.state.sim
    topics = [t for t in getattr(s, "smn_topics", {}).values() if t["project_id"] == pid]
    return {"topic_count": len(topics), "topics": [
        {"name": t["name"], "topic_urn": t["topic_urn"], "display_name": t["display_name"]} for t in topics]}

@router.delete("/v2/{pid}/notifications/topics/{topic_urn}")
async def delete_topic(request: Request, pid: str, topic_urn: str):
    s = request.app.state.sim
    for tid, t in list(getattr(s, "smn_topics", {}).items()):
        if t["topic_urn"] == topic_urn or t["name"] == topic_urn:
            del s.smn_topics[tid]
            return {"request_id": new_id()}
    return JSONResponse({"error_msg": "Topic not found", "error_code": "SMN.0001"}, status_code=404)

@router.post("/v2/{pid}/notifications/topics/{topic_urn}/subscriptions")
async def subscribe(request: Request, pid: str, topic_urn: str):
    s = request.app.state.sim
    for t in getattr(s, "smn_topics", {}).values():
        if t["topic_urn"] == topic_urn or t["name"] == topic_urn:
            body = await request.json()
            sub = {"id": new_id(), "endpoint": body.get("endpoint", ""),
                   "protocol": body.get("protocol", "email"), "remark": body.get("remark", "")}
            sub["subscription_urn"] = f"urn:smn:sim:{pid}:{sub['id']}"
            t["subscriptions"].append(sub)
            return {"subscription_urn": sub["subscription_urn"], "request_id": new_id()}
    return JSONResponse({"error_msg": "Topic not found", "error_code": "SMN.0001"}, status_code=404)

@router.post("/v2/{pid}/notifications/topics/{topic_urn}/publish")
async def publish(request: Request, pid: str, topic_urn: str):
    body = await request.json()
    return {"message_id": new_id(), "request_id": new_id(),
            "subject": body.get("subject", ""), "message": body.get("message", "")}


# ---------------------------------------------------------------------------
# sub-APIs: subscription management + topic details
# ---------------------------------------------------------------------------

@router.get("/v2/{pid}/notifications/topics/{topic_urn}/subscriptions")
async def list_subscriptions(request: Request, pid: str, topic_urn: str):
    s = request.app.state.sim
    t = next((x for x in getattr(s, "smn_topics", {}).values()
              if x["topic_urn"] == topic_urn or x["name"] == topic_urn), None)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "SMN.0001", "error_msg": "topic not found"},
                            status_code=404)
    return {"subscriptions": t.get("subscriptions", [])}


@router.delete("/v2/{pid}/notifications/topics/{topic_urn}/subscriptions/{sub_urn}")
async def delete_subscription(request: Request, pid: str, topic_urn: str, sub_urn: str):
    s = request.app.state.sim
    t = next((x for x in getattr(s, "smn_topics", {}).values()
              if x["topic_urn"] == topic_urn or x["name"] == topic_urn), None)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "SMN.0001", "error_msg": "topic not found"},
                            status_code=404)
    before = len(t.get("subscriptions", []))
    t["subscriptions"] = [x for x in t.get("subscriptions", [])
                          if x.get("subscription_urn") != sub_urn]
    if len(t["subscriptions"]) == before:
        return JSONResponse({"error_code": "SMN.0002",
                             "error_msg": "subscription not found"}, status_code=404)
    return Response(status_code=204)


@router.get("/v2/{pid}/notifications/topics/{topic_urn}")
async def show_topic(request: Request, pid: str, topic_urn: str):
    s = request.app.state.sim
    t = next((x for x in getattr(s, "smn_topics", {}).values()
              if x["topic_urn"] == topic_urn or x["name"] == topic_urn), None)
    if not t or t["project_id"] != pid:
        return JSONResponse({"error_code": "SMN.0001", "error_msg": "topic not found"},
                            status_code=404)
    return t


@router.post("/v2/{pid}/notifications/message_templates")
async def create_message_template(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "smn_templates"):
        s.smn_templates = {}
    body = await request.json()
    name = body.get("message_template_name", "")
    if not name:
        return JSONResponse({"error_code": "SMN.0003",
                             "error_msg": "message_template_name is required"}, status_code=400)
    tid = new_id()
    s.smn_templates[tid] = {
        "message_template_id": tid, "name": name,
        "protocol": body.get("protocol", "email"),
        "content": body.get("content", ""),
        "tag_names": body.get("tag_names", []),
        "project_id": pid, "created_at": now_millis(),
    }
    return {"message_template_id": tid, "name": name}


@router.get("/v2/{pid}/notifications/message_templates")
async def list_message_templates(request: Request, pid: str):
    s = request.app.state.sim
    tpls = [t for t in getattr(s, "smn_templates", {}).values() if t["project_id"] == pid]
    return {"message_templates": tpls, "count": len(tpls)}
