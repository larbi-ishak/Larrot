"""IoTDA: IoT Device Access: products, devices."""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis
router = APIRouter()

@router.post("/v5/iot/{pid}/products")
async def create_product(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "iot_products"): s.iot_products = {}
    body = await request.json()
    prod_id = new_id()
    s.iot_products[prod_id] = {"product_id": prod_id, "name": body.get("product_name", f"prod-{prod_id[:8]}"),
        "protocol_type": body.get("protocol_type", "MQTT"),
        "data_format": body.get("data_format", "json"),
        "created_at": now_millis(), "project_id": pid}
    return {"product_id": prod_id, "name": s.iot_products[prod_id]["name"]}

@router.get("/v5/iot/{pid}/products")
async def list_products(request: Request, pid: str):
    s = request.app.state.sim
    products = [p for p in getattr(s, "iot_products", {}).values() if p["project_id"] == pid]
    return {"products": products, "total": len(products)}

@router.post("/v5/iot/{pid}/devices")
async def create_device(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "iot_devices"): s.iot_devices = {}
    body = await request.json()
    dev_id = new_id()
    s.iot_devices[dev_id] = {"device_id": dev_id, "name": body.get("device_name", f"dev-{dev_id[:8]}"),
        "product_id": body.get("product_id", ""), "status": "ONLINE",
        "created_at": now_millis(), "project_id": pid}
    return {"device_id": dev_id, "name": s.iot_devices[dev_id]["name"]}

@router.get("/v5/iot/{pid}/devices")
async def list_devices(request: Request, pid: str):
    s = request.app.state.sim
    devices = [d for d in getattr(s, "iot_devices", {}).values() if d["project_id"] == pid]
    return {"devices": devices, "total": len(devices)}

@router.delete("/v5/iot/{pid}/devices/{device_id}")
async def delete_device(request: Request, pid: str, device_id: str):
    s = request.app.state.sim
    if device_id not in getattr(s, "iot_devices", {}):
        return JSONResponse({"error_msg": "Device not found", "error_code": "IoT.0001"}, status_code=404)
    del s.iot_devices[device_id]
    return Response(status_code=204)


@router.post("/v5/iot/{pid}/devices/{device_id}/commands")
async def send_command(request: Request, pid: str, device_id: str):
    s = request.app.state.sim
    dev = getattr(s, "iot_devices", {}).get(device_id)
    if not dev or dev.get("project_id") != pid:
        return JSONResponse({"error_code": "IOTDA.00001",
                             "error_msg": "device not found"}, status_code=404)
    body = await request.json()
    return {"command_id": new_id(), "service_id": body.get("service_id", ""),
            "command_name": body.get("command_name", ""),
            "status": "PENDING", "result": None}
