"""AOM: Application Operations Management: apps, components, alarms."""
from fastapi import APIRouter, Request

from ..core.jobs import new_id

router = APIRouter()

@router.post("/v1/{pid}/aom/apps")
async def create_app(request: Request, pid: str):
    """Register an application in AOM: the unit that groups components for monitoring."""
    body = await request.json()
    return {"app_id": new_id(), "name": body.get("name", "my-app")}

@router.get("/v1/{pid}/aom/apps")
async def list_apps(request: Request, pid: str):
    """List registered AOM applications."""
    return {"apps": [], "total": 0}

@router.post("/v1/{pid}/aom/components")
async def create_component(request: Request, pid: str):
    """Register a component under an application: one deployable service instance."""
    body = await request.json()
    return {"component_id": new_id(), "name": body.get("name", "my-component")}

@router.get("/v1/{pid}/aom/alarms")
async def list_aom_alarms(request: Request, pid: str):
    """List current alarms across monitored applications and components."""
    return {"alarms": [], "total": 0}

@router.post("/v2/{pid}/aom/alarm-rules")
async def create_alarm_rule(request: Request, pid: str):
    """Create an alarm rule: a metric threshold that fires an alarm when crossed."""
    body = await request.json()
    return {"rule_id": new_id(), "name": body.get("name", "my-rule")}
