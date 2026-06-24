# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from create_spot_vm import create_spot_vm
from model_registry import MODEL_REGISTRY

app = FastAPI(
    title="Cloud Burst Inference Gateway",
    description="API to launch Spot VMs with selected models",
    version="1.0"
)

class LaunchRequest(BaseModel):
    model_name: str
    zone: str = "us-central1-b"

@app.get("/")
def root():
    return {
        "message": "Cloud Burst Gateway is running",
        "available_models": list(MODEL_REGISTRY.keys())
    }

@app.post("/launch")
def launch_spot_vm(request: LaunchRequest):
    model_name = request.model_name

    if model_name not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    try:
        vm_name = create_spot_vm(
            project_id="project-5ca47de0-b0a2-43a7-aed",  # ← Change this
            zone=request.zone,
            model_name=model_name
        )
        return {
            "message": f"Spot VM launched successfully for model: {model_name}",
            "vm_name": vm_name,
            "status": "provisioning",
            "note": "The VM is starting. Inference server will be available on port 8000 shortly."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models")
def list_models():
    return {"available_models": MODEL_REGISTRY}