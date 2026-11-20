"""ModelArts: ML development: notebooks, training jobs, model management,
inference services, fine-tuning, and MaaS (Model-as-a-Service).

MaaS exposes OpenAI-compatible endpoints (GET /v1/models, POST /v1/chat/completions,
POST /v1/embeddings) plus API-key management: mirroring ModelArts Studio.
"""
import hashlib
import time

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from ..core.jobs import new_id, now_millis

router = APIRouter()

# Models available through MaaS (mirrors the ModelArts Studio model list)
MAAS_MODELS = [
    {"id": "DeepSeek-V3", "owned_by": "deepseek", "model_type": "chat"},
    {"id": "DeepSeek-R1", "owned_by": "deepseek", "model_type": "reasoning"},
    {"id": "Qwen2.5-72B-Instruct", "owned_by": "qwen", "model_type": "chat"},
    {"id": "Qwen2.5-Coder-32B", "owned_by": "qwen", "model_type": "code"},
    {"id": "Pangu-N4B", "owned_by": "huawei", "model_type": "chat"},
    {"id": "bge-m3", "owned_by": "bge", "model_type": "embedding"},
]


# ---------------------------------------------------------------------------
# notebooks
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/notebooks")
async def create_notebook(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_notebooks"):
        s.ma_notebooks = {}
    body = await request.json()
    nid = new_id()
    s.ma_notebooks[nid] = {"id": nid, "name": body.get("name", f"nb-{nid[:8]}"),
        "flavor": body.get("flavor", "modelarts.kat1.xlarge"),
        "status": "CREATING", "image_id": body.get("image_id", ""),
        "created_at": now_millis(), "project_id": pid}

    async def effect():
        nb = s.ma_notebooks.get(nid)
        if nb:
            nb["status"] = "RUNNING"
        return None

    await s.jobs.submit("createNotebook", {"notebook_id": nid}, effect)
    return {"id": nid, "name": s.ma_notebooks[nid]["name"], "status": "CREATING"}


@router.get("/v2/{pid}/notebooks")
async def list_notebooks(request: Request, pid: str):
    s = request.app.state.sim
    notebooks = [n for n in getattr(s, "ma_notebooks", {}).values()
                 if n["project_id"] == pid]
    return {"notebooks": notebooks, "total": len(notebooks)}


@router.delete("/v2/{pid}/notebooks/{notebook_id}")
async def delete_notebook(request: Request, pid: str, notebook_id: str):
    s = request.app.state.sim
    nb = getattr(s, "ma_notebooks", {}).get(notebook_id)
    if not nb or nb["project_id"] != pid:
        return JSONResponse({"error_msg": "Notebook not found",
                              "error_code": "MA.0001"}, status_code=404)
    del s.ma_notebooks[notebook_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# training jobs
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/training-jobs")
async def create_training_job(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_training_jobs"):
        s.ma_training_jobs = {}
    body = await request.json()
    jid = new_id()
    s.ma_training_jobs[jid] = {
        "id": jid, "name": body.get("name", f"job-{jid[:8]}"),
        "status": "SUBMITTED", "flavor": body.get("flavor", "modelarts.kat1.xlarge"),
        "algorithm": body.get("algorithm", {}), "created_at": now_millis(),
        "project_id": pid}

    async def effect():
        j = s.ma_training_jobs.get(jid)
        if j:
            j["status"] = "SUCCEEDED"
        return None

    await s.jobs.submit("runTrainingJob", {"job_id": jid}, effect)
    return {"id": jid, "name": s.ma_training_jobs[jid]["name"], "status": "SUBMITTED"}


@router.get("/v2/{pid}/training-jobs")
async def list_training_jobs(request: Request, pid: str):
    s = request.app.state.sim
    jobs = [j for j in getattr(s, "ma_training_jobs", {}).values()
            if j["project_id"] == pid]
    return {"jobs": jobs, "total": len(jobs)}


# ---------------------------------------------------------------------------
# model management (v1 model registry)
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/models")
async def register_model(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_models"):
        s.ma_models = {}
    body = await request.json()
    name = body.get("model_name", "")
    if not name:
        return JSONResponse({"error_code": "MA.0002",
                             "error_msg": "model_name is required"}, status_code=400)
    mid = new_id()
    s.ma_models[mid] = {
        "model_id": mid, "model_name": name,
        "model_type": body.get("model_type", "TensorFlow"),
        "model_version": body.get("model_version", "1.0.0"),
        "engine": body.get("engine", "TensorFlow-2.1"),
        "status": "publishing", "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        m = s.ma_models.get(mid)
        if m:
            m["status"] = "published"
        return None

    await s.jobs.submit("publishModel", {"model_id": mid}, effect)
    return {"model_id": mid, "model_name": name, "status": "publishing"}


@router.get("/v1/{pid}/models")
async def list_models(request: Request, pid: str):
    s = request.app.state.sim
    models = [m for m in getattr(s, "ma_models", {}).values()
              if m["project_id"] == pid]
    return {"models": models, "total": len(models), "count": len(models)}


@router.get("/v1/{pid}/models/{model_id}")
async def show_model(request: Request, pid: str, model_id: str):
    s = request.app.state.sim
    m = getattr(s, "ma_models", {}).get(model_id)
    if not m or m["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0003", "error_msg": "model not found"},
                            status_code=404)
    return m


@router.delete("/v1/{pid}/models/{model_id}")
async def delete_model(request: Request, pid: str, model_id: str):
    s = request.app.state.sim
    m = getattr(s, "ma_models", {}).get(model_id)
    if not m or m["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0003", "error_msg": "model not found"},
                            status_code=404)
    del s.ma_models[model_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# inference services (deploy a model as a service)
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/services")
async def create_service(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_services"):
        s.ma_services = {}
    body = await request.json()
    model_id = body.get("model_id", "")
    model = getattr(s, "ma_models", {}).get(model_id)
    if not model or model["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0003", "error_msg": "model not found"},
                            status_code=404)
    if model["status"] != "published":
        return JSONResponse({"error_code": "MA.0004",
                             "error_msg": "model is not published"}, status_code=400)
    sid = new_id()
    s.ma_services[sid] = {
        "service_id": sid, "service_name": body.get("service_name", f"svc-{sid[:8]}"),
        "model_id": model_id, "model_name": model["model_name"],
        "spec": body.get("spec", "modelarts.kat1.xlarge"),
        "status": "deploying", "replicas": body.get("replicas", 1),
        "endpoint": f"https://endpoint.modelarts.myhuaweicloud.com/v1/infers/{sid[:8]}",
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        svc = s.ma_services.get(sid)
        if svc:
            svc["status"] = "running"
        return None

    await s.jobs.submit("deployModelService", {"service_id": sid}, effect)
    return {"service_id": sid, "service_name": s.ma_services[sid]["service_name"],
            "status": "deploying"}


@router.get("/v1/{pid}/services")
async def list_services(request: Request, pid: str):
    s = request.app.state.sim
    services = [x for x in getattr(s, "ma_services", {}).values()
                if x["project_id"] == pid]
    return {"services": services, "total": len(services), "count": len(services)}


@router.get("/v1/{pid}/services/{service_id}")
async def show_service(request: Request, pid: str, service_id: str):
    s = request.app.state.sim
    svc = getattr(s, "ma_services", {}).get(service_id)
    if not svc or svc["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0005", "error_msg": "service not found"},
                            status_code=404)
    return svc


@router.delete("/v1/{pid}/services/{service_id}")
async def delete_service(request: Request, pid: str, service_id: str):
    s = request.app.state.sim
    svc = getattr(s, "ma_services", {}).get(service_id)
    if not svc or svc["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0005", "error_msg": "service not found"},
                            status_code=404)
    del s.ma_services[service_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# fine-tuning jobs
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/fine-tuning-jobs")
async def create_fine_tuning_job(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_finetune_jobs"):
        s.ma_finetune_jobs = {}
    body = await request.json()
    base_model = body.get("base_model", "")
    if not any(m["id"] == base_model for m in MAAS_MODELS):
        return JSONResponse({"error_code": "MA.0006",
                             "error_msg": f"unknown base_model: {base_model}"},
                            status_code=400)
    fid = new_id()
    s.ma_finetune_jobs[fid] = {
        "job_id": fid, "name": body.get("name", f"sft-{fid[:8]}"),
        "base_model": base_model, "dataset_id": body.get("dataset_id", ""),
        "hyperparameters": body.get("hyperparameters", {"epochs": 3, "lr": 1e-5}),
        "status": "SUBMITTED", "progress": 0,
        "project_id": pid, "created_at": now_millis(),
    }

    async def effect():
        j = s.ma_finetune_jobs.get(fid)
        if j:
            j["status"] = "SUCCEEDED"
            j["progress"] = 100
        return None

    await s.jobs.submit("runFineTuning", {"job_id": fid}, effect)
    return {"job_id": fid, "status": "SUBMITTED"}


@router.get("/v1/{pid}/fine-tuning-jobs")
async def list_fine_tuning_jobs(request: Request, pid: str):
    s = request.app.state.sim
    jobs = [j for j in getattr(s, "ma_finetune_jobs", {}).values()
            if j["project_id"] == pid]
    return {"jobs": jobs, "total": len(jobs)}


# ---------------------------------------------------------------------------
# MaaS: OpenAI-compatible inference (account-level, no project in path)
# ---------------------------------------------------------------------------

@router.get("/v1/models")
async def maas_list_models():
    """OpenAI-compatible model list."""
    return {"object": "list", "data": [dict(m) for m in MAAS_MODELS]}


@router.post("/v1/chat/completions")
async def maas_chat_completions(request: Request):
    """OpenAI-compatible chat completion (deterministic simulated output)."""
    body = await request.json()
    model = body.get("model", "DeepSeek-V3")
    if not any(m["id"] == model for m in MAAS_MODELS):
        return JSONResponse({
            "error": {"message": f"The model '{model}' does not exist",
                      "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=404)
    messages = body.get("messages", [])
    if not messages:
        return JSONResponse({
            "error": {"message": "messages is required",
                      "type": "invalid_request_error", "code": "empty_messages"}},
            status_code=400)
    prompt = messages[-1].get("content", "") if messages else ""
    reply = (f"[sim:{model}] You said: {prompt}. This is a deterministic "
             f"simulated completion from huawei-sim MaaS.")
    prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4 + 1
    completion_tokens = len(reply) // 4 + 1
    return {
        "id": f"chatcmpl-{new_id()[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": prompt_tokens,
                  "completion_tokens": completion_tokens,
                  "total_tokens": prompt_tokens + completion_tokens},
    }


@router.post("/v1/embeddings")
async def maas_embeddings(request: Request):
    """OpenAI-compatible embeddings (deterministic hash-based vectors)."""
    body = await request.json()
    model = body.get("model", "bge-m3")
    if not any(m["id"] == model for m in MAAS_MODELS):
        return JSONResponse({
            "error": {"message": f"The model '{model}' does not exist",
                      "type": "invalid_request_error", "code": "model_not_found"}},
            status_code=404)
    inputs = body.get("input", [])
    if isinstance(inputs, str):
        inputs = [inputs]
    if not inputs:
        return JSONResponse({
            "error": {"message": "input is required",
                      "type": "invalid_request_error", "code": "empty_input"}},
            status_code=400)
    data = []
    for i, text in enumerate(inputs):
        digest = hashlib.sha256(str(text).encode()).digest()
        vector = [b / 255.0 for b in digest[:32]]
        data.append({"object": "embedding", "index": i, "embedding": vector})
    return {"object": "list", "data": data,
            "model": model,
            "usage": {"prompt_tokens": sum(len(str(t)) for t in inputs) // 4 + 1,
                      "total_tokens": sum(len(str(t)) for t in inputs) // 4 + 1}}


# ---------------------------------------------------------------------------
# MaaS API keys
# ---------------------------------------------------------------------------

@router.post("/v1/{pid}/maas/keys")
async def create_api_key(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "maas_keys"):
        s.maas_keys = {}
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "MA.0007", "error_msg": "name is required"},
                            status_code=400)
    kid = new_id()
    secret = f"sk-sim-{new_id()}"
    s.maas_keys[kid] = {
        "key_id": kid, "name": name, "key": secret,
        "status": "active", "project_id": pid, "created_at": now_millis(),
    }
    return {"key_id": kid, "name": name, "key": secret,
            "note": "store this key now: it is not retrievable later"}


@router.get("/v1/{pid}/maas/keys")
async def list_api_keys(request: Request, pid: str):
    s = request.app.state.sim
    keys = [{"key_id": k["key_id"], "name": k["name"], "status": k["status"],
             "created_at": k["created_at"]}
            for k in getattr(s, "maas_keys", {}).values() if k["project_id"] == pid]
    return {"keys": keys, "total": len(keys)}


@router.delete("/v1/{pid}/maas/keys/{key_id}")
async def delete_api_key(request: Request, pid: str, key_id: str):
    s = request.app.state.sim
    k = getattr(s, "maas_keys", {}).get(key_id)
    if not k or k["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0008", "error_msg": "key not found"},
                            status_code=404)
    del s.maas_keys[key_id]
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# datasets
# ---------------------------------------------------------------------------

@router.post("/v2/{pid}/datasets")
async def create_dataset(request: Request, pid: str):
    s = request.app.state.sim
    if not hasattr(s, "ma_datasets"):
        s.ma_datasets = {}
    body = await request.json()
    name = body.get("dataset_name", "")
    if not name:
        return JSONResponse({"error_code": "MA.0009",
                             "error_msg": "dataset_name is required"}, status_code=400)
    did = new_id()
    s.ma_datasets[did] = {
        "dataset_id": did, "dataset_name": name,
        "data_type": body.get("data_type", 0),
        "data_source": body.get("data_source", {}),
        "status": "INIT", "samples": 0,
        "project_id": pid, "created_at": now_millis(),
    }
    return {"dataset_id": did, "dataset_name": name}


@router.get("/v2/{pid}/datasets")
async def list_datasets(request: Request, pid: str):
    s = request.app.state.sim
    ds = [d for d in getattr(s, "ma_datasets", {}).values() if d["project_id"] == pid]
    return {"datasets": ds, "total": len(ds)}


@router.delete("/v2/{pid}/datasets/{dataset_id}")
async def delete_dataset(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    del s.ma_datasets[dataset_id]
    return Response(status_code=204)


@router.post("/v2/{pid}/datasets/{dataset_id}/versions")
async def create_dataset_version(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    vid = new_id()
    version = {"version_id": vid, "version_name": body.get("version_name", f"v-{vid[:8]}"),
               "status": "PENDING", "samples": d.get("samples", 0),
               "dataset_id": dataset_id, "project_id": pid, "created_at": now_millis()}
    d.setdefault("versions", []).append(version)

    async def effect():
        v = next((x for x in d.get("versions", []) if x["version_id"] == vid), None)
        if v:
            v["status"] = "ACTIVE"
        return None

    await s.jobs.submit("createDatasetVersion", {"version_id": vid}, effect)
    return {"version_id": vid, "status": "PENDING"}


@router.get("/v2/{pid}/datasets/{dataset_id}/versions")
async def list_dataset_versions(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return {"versions": d.get("versions", []), "total": len(d.get("versions", []))}


@router.get("/v2/{pid}/datasets/{dataset_id}")
async def show_dataset(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return d


@router.get("/v2/{pid}/datasets/{dataset_id}/labels")
async def list_labels(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return {"labels": d.get("labels", []), "total": len(d.get("labels", []))}


@router.post("/v2/{pid}/datasets/{dataset_id}/labels")
async def create_label(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    name = body.get("name", "")
    if not name:
        return JSONResponse({"error_code": "MA.0011", "error_msg": "label name is required"},
                            status_code=400)
    labels = d.setdefault("labels", [])
    if any(x["name"] == name for x in labels):
        return JSONResponse({"error_code": "MA.0012", "error_msg": "label already exists"},
                            status_code=409)
    label = {"name": name, "type": body.get("type", 0), "property": body.get("property", {})}
    labels.append(label)
    return {"labels": [label]}


@router.put("/v2/{pid}/datasets/{dataset_id}/labels/{label_name}")
async def update_label(request: Request, pid: str, dataset_id: str, label_name: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    label = next((x for x in d.get("labels", []) if x["name"] == label_name), None)
    if not label:
        return JSONResponse({"error_code": "MA.0013", "error_msg": "label not found"},
                            status_code=404)
    body = await request.json()
    if "name" in body and body["name"]:
        label["name"] = body["name"]
    if "type" in body:
        label["type"] = body["type"]
    return {"labels": [label]}


@router.delete("/v2/{pid}/datasets/{dataset_id}/labels/{label_name}")
async def delete_label(request: Request, pid: str, dataset_id: str, label_name: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    before = len(d.get("labels", []))
    d["labels"] = [x for x in d.get("labels", []) if x["name"] != label_name]
    if len(d["labels"]) == before:
        return JSONResponse({"error_code": "MA.0013", "error_msg": "label not found"},
                            status_code=404)
    return Response(status_code=204)


@router.post("/v2/{pid}/datasets/{dataset_id}/samples")
async def add_samples(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    samples_in = body.get("samples", [])
    if not samples_in:
        return JSONResponse({"error_code": "MA.0014", "error_msg": "samples is required"},
                            status_code=400)
    store = d.setdefault("samples_list", [])
    added = []
    for smp in samples_in:
        sid = new_id()
        store.append({"sample_id": sid, "source": smp.get("source", ""),
                       "labels": smp.get("labels", [])})
        added.append(sid)
    d["samples"] = len(store)
    return {"sample_ids": added}


@router.get("/v2/{pid}/datasets/{dataset_id}/samples")
async def list_samples(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return {"samples": d.get("samples_list", []),
            "total": len(d.get("samples_list", []))}


@router.post("/v2/{pid}/datasets/{dataset_id}/import-tasks")
async def create_import_task(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    tid = new_id()
    task = {"task_id": tid, "task_type": body.get("task_type", "import"),
             "status": "RUNNING", "dataset_id": dataset_id,
             "source": body.get("import_path", ""),
             "imported_sample": 0, "project_id": pid, "created_at": now_millis()}
    d.setdefault("import_tasks", []).append(task)

    async def effect():
        t = next((x for x in d.get("import_tasks", []) if x["task_id"] == tid), None)
        if t:
            t["status"] = "COMPLETED"
            t["imported_sample"] = 10
        return None

    await s.jobs.submit("runImportTask", {"task_id": tid}, effect)
    return {"task_id": tid, "status": "RUNNING"}


@router.get("/v2/{pid}/datasets/{dataset_id}/import-tasks")
async def list_import_tasks(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return {"import_tasks": d.get("import_tasks", []),
            "total": len(d.get("import_tasks", []))}


@router.delete("/v2/{pid}/datasets/{dataset_id}/versions/{version_id}")
async def delete_dataset_version(request: Request, pid: str, dataset_id: str, version_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    before = len(d.get("versions", []))
    d["versions"] = [v for v in d.get("versions", []) if v["version_id"] != version_id]
    if len(d["versions"]) == before:
        return JSONResponse({"error_code": "MA.0015", "error_msg": "version not found"},
                            status_code=404)
    return Response(status_code=204)


@router.post("/v2/{pid}/datasets/{dataset_id}/export-tasks")
async def create_export_task(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    tid = new_id()
    task = {"task_id": tid, "task_type": body.get("task_type", "export"),
             "status": "RUNNING", "dataset_id": dataset_id,
             "export_path": body.get("export_path", ""),
             "exported_sample": 0, "project_id": pid, "created_at": now_millis()}
    d.setdefault("export_tasks", []).append(task)

    async def effect():
        t = next((x for x in d.get("export_tasks", []) if x["task_id"] == tid), None)
        if t:
            t["status"] = "COMPLETED"
            t["exported_sample"] = d.get("samples", 0)
        return None

    await s.jobs.submit("runExportTask", {"task_id": tid}, effect)
    return {"task_id": tid, "status": "RUNNING"}


@router.get("/v2/{pid}/datasets/{dataset_id}/export-tasks")
async def list_export_tasks(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    return {"export_tasks": d.get("export_tasks", []),
            "total": len(d.get("export_tasks", []))}


@router.put("/v2/{pid}/datasets/{dataset_id}")
async def update_dataset(request: Request, pid: str, dataset_id: str):
    s = request.app.state.sim
    d = getattr(s, "ma_datasets", {}).get(dataset_id)
    if not d or d["project_id"] != pid:
        return JSONResponse({"error_code": "MA.0010", "error_msg": "dataset not found"},
                            status_code=404)
    body = await request.json()
    for field in ("dataset_name", "description", "data_source"):
        if field in body:
            d[field] = body[field]
    return d
