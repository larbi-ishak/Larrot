"""BSS: Billing Service: orders, resources, balances."""
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/v2/orders/customer-orders")
async def list_orders(request: Request):
    return {"total_count": 0, "orders": []}

@router.get("/v2/orders/customer-orders/resources")
async def list_order_resources(request: Request):
    return {"total_count": 0, "resources": []}

@router.get("/v2/accounts/customer-accounts/balances")
async def get_balance(request: Request):
    return {"currency": "USD", "account_details": [{"amount": 100.0, "type": "balance"}]}

@router.post("/v2/orders/customer-orders/pay")
async def pay_order(request: Request):
    body = await request.json()
    return {"order_id": body.get("order_id", ""), "success": True}
