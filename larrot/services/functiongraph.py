"""FunctionGraph: serverless function management and invocation."""

import time

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from ..core.jobs import new_id, now_millis

router = APIRouter()


def _func_json(f):
    return {
        "func_id": f["id"], "func_name": f["name"],
        "package": f.get("package", "default"),
        "runtime": f.get("runtime", "Python3.9"),
        "handler": f.get("handler", "index.handler"),
        "timeout": f.get("timeout", 3),
        "memory_size": f.get("memory_size", 128),
        "code_type": f.get("code_type", "inline"),
        "code_size": len(f.get("code", "")),
        "digest": f.get("digest", ""),
        "version": f.get("version", "latest"),
        "last_modified": f["updated_at"],
        "created_at": f["created_at"],
    }


@router.post("/v2/{pid}/fg/functions")
async def create_function(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "fg_functions"):
        state.fg_functions = {}
    body = await request.json()
    func_id = new_id()
    now = now_millis()
    state.fg_functions[func_id] = {
        "id": func_id, "name": body.get("func_name", f"func-{func_id[:8]}"),
        "package": body.get("package", "default"),
        "runtime": body.get("runtime", "Python3.9"),
        "handler": body.get("handler", "index.handler"),
        "timeout": body.get("timeout", 3),
        "memory_size": body.get("memory_size", 128),
        "code_type": body.get("code_type", "inline"),
        "code": body.get("code", ""),
        "version": "latest",
        "created_at": now, "updated_at": now, "project_id": pid,
    }
    return {"func_id": func_id, "func_info": _func_json(state.fg_functions[func_id])}


@router.get("/v2/{pid}/fg/functions")
async def list_functions(request: Request, pid: str):
    state = request.app.state.sim
    if not hasattr(state, "fg_functions"):
        state.fg_functions = {}
    funcs = [f for f in state.fg_functions.values() if f["project_id"] == pid]
    return {"functions": [_func_json(f) for f in funcs], "count": len(funcs)}


@router.get("/v2/{pid}/fg/functions/{func_id}")
async def show_function(request: Request, pid: str, func_id: str):
    state = request.app.state.sim
    f = getattr(state, "fg_functions", {}).get(func_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_msg": "Function not found", "error_code": "FG.0101"}, status_code=404)
    return {"func_info": _func_json(f)}


@router.delete("/v2/{pid}/fg/functions/{func_id}")
async def delete_function(request: Request, pid: str, func_id: str):
    state = request.app.state.sim
    if func_id not in state.fg_functions:
        return JSONResponse({"error_msg": "Function not found", "error_code": "FG.0101"}, status_code=404)
    del state.fg_functions[func_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/fg/functions/{func_id}/invocations")
async def invoke_function(request: Request, pid: str, func_id: str):
    """Invoke a function: simulates execution and returns a result."""
    state = request.app.state.sim
    f = getattr(state, "fg_functions", {}).get(func_id)
    if not f or f["project_id"] != pid:
        return JSONResponse({"error_msg": "Function not found", "error_code": "FG.0101"}, status_code=404)

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    event = body.get("event", {})

    start = time.time()
    # Simulate execution: parse the code and try to extract a return value
    code = f.get("code", "")
    result = {"message": "Function executed successfully", "event": event}
    if "return" in code:
        # Try to extract the return value (very naive)
        import re
        m = re.search(r'return\s+(.+)', code)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            try:
                # literal_eval only: eval() here would let any web page that can
                # reach localhost:8200 execute arbitrary code on the dev machine
                import ast
                val = ast.literal_eval(val)
            except Exception:
                pass
            result["result"] = val
    elapsed = int((time.time() - start) * 1000)

    return {
        "execution_time": max(elapsed, 1),
        "function_arn": f"urn:fg:sim:{pid}:function:{f['name']}:latest",
        "log": f"START RequestId: {new_id()}\nEND RequestId: {new_id()}",
        "result": result,
        "status": "success",
    }
