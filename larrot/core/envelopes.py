"""Per-service error body envelopes (API_DOCS_RESEARCH §8).

Huawei Cloud does NOT use one global error shape: each service family has its own.
"""

from .jobs import new_request_id


def ecs_error(code: str, message: str, details: list | None = None) -> dict:
    """ECS: nested {"error": {"code", "message", "details"?}}"""
    err = {"code": code, "message": message}
    if details:
        err["details"] = [{"code": c, "message": m} for c, m in details]
    return {"error": err}


def evs_error(code: str, message: str) -> dict:
    """EVS native v2: nested, message first in doc examples."""
    return {"error": {"message": message, "code": code}}


def vpc_error(code: str, message: str) -> dict:
    """VPC/EIP v1: flat {"code", "message"}: NOT error_code/error_msg."""
    return {"code": code, "message": message}


def apigw_error(code: str, message: str) -> dict:
    """API Gateway: flat with request_id."""
    return {"error_msg": message, "error_code": code, "request_id": new_request_id()}


def ims_error(message: str) -> dict:
    """IMS: flat gateway-style."""
    return {"error_msg": message, "error_code": "IMG.0001", "request_id": new_request_id()}


def cbr_error(code: str, message: str) -> dict:
    """CBR v3: flat gateway-style."""
    return {"error_msg": message, "error_code": code, "request_id": new_request_id()}
