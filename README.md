# Spot VM — Cloud Burst Inference

A cost-aware ML inference system that runs models locally when resources allow, and automatically bursts to Google Cloud Spot VMs when local CPU or memory is exhausted. A FastAPI gateway also lets you provision Spot VMs on demand for any model in the registry.

## Overview

This project implements a **local-first, cloud-burst** pattern for running transformer models:

1. **Local inference** — Run models on your machine using Hugging Face Transformers.
2. **Resource monitoring** — A background monitor watches CPU and memory usage.
3. **Cloud burst** — When thresholds are exceeded, a preemptible Spot VM is provisioned automatically.
4. **On-demand launch** — The gateway API can spin up Spot VMs for a specific model at any time.

Models are stored in **Google Cloud Storage (GCS)** and pulled onto VMs at startup. Spot VMs keep inference costs low while still providing burst capacity when you need it.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Local Machine                           │
│                                                                 │
│  ┌──────────────┐   ┌────────────────────┐   ┌─────────────┐ │
│  │  inference   │   │ cloud_burst_monitor │   │  local_test │ │
│  │  (code/)     │   │     (cloud/)        │   │  (local/)   │ │
│  └──────┬───────┘   └──────────┬─────────┘   └─────────────┘ │
│         │                      │                                │
│         │            CPU > 90% or Memory > 70%                   │
│         │                      ▼                                │
│         │            ┌────────────────────┐                    │
│         │            │  create_spot_vm    │                    │
│         │            │     (cloud/)       │                    │
│         │            └──────────┬─────────┘                    │
└─────────┼──────────────────────┼───────────────────────────────┘
          │                      │
          │         ┌────────────▼────────────┐
          │         │   FastAPI Gateway       │
          │         │      (gateway/)         │
          │         │  POST /launch           │
          │         │  GET  /models           │
          │         └────────────┬────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                        │
│                                                                 │
│  ┌──────────────┐         ┌─────────────────────────────────┐ │
│  │     GCS      │────────▶│         Spot VM (n2-standard-8) │ │
│  │ Model Store  │         │  startup.sh → download model    │ │
│  │              │         │  inference server on port 8001  │ │
│  └──────────────┘         │  shutdown.sh → save checkpoints │ │
│                           └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
Spot_VM_Project/
├── gateway/                  # FastAPI inference gateway
│   ├── app.py                # REST API — launch VMs, list models
│   ├── model_registry.py     # Registered models and GCS paths
│   ├── spot_vm_manager.py    # VM lifecycle management (planned)
│   └── requirements.txt
│
├── cloud/                    # GCP infrastructure
│   ├── create_spot_vm.py     # Provision Spot VMs via Compute Engine API
│   ├── cloud_burst_monitor.py# Monitor local resources and trigger burst
│   ├── gcs_utils.py          # Upload, download, and stream models from GCS
│   ├── startup.sh            # VM startup: fetch model, install deps, serve
│   ├── shutdown.sh           # VM preemption: persist checkpoints to GCS
│   └── README.md
│
├── code/                     # ML workloads
│   ├── inference.py          # Local seq2seq inference (Transformers)
│   ├── train.py              # Model training (planned)
│   └── requirements.txt
│
└── local/                    # Local development and testing
    └── local_test.py
```

## Model Registry

Models are defined in `gateway/model_registry.py`. Each entry maps a name to a GCS path, description, and inference engine.

| Model       | Engine        | Status    | Description                          |
|-------------|---------------|-----------|--------------------------------------|
| `t5-small`  | transformers  | Active    | Lightweight summarization model      |
| `llama3-8b` | vllm          | Planned   | Meta Llama 3 8B Instruct             |
| `qwen2.5-7b`| vllm          | Planned   | Qwen 2.5 7B Instruct                 |
| `deepseek-v3`| vllm         | Planned   | DeepSeek V3                          |

Default GCS location: `gs://ai-model-registry-aice/<model>/<version>/`

## Prerequisites

- Python 3.10+
- A Google Cloud project with:
  - Compute Engine API enabled
  - Cloud Storage API enabled
  - A GCS bucket containing model artifacts
  - A service account (`ml-spot-vm-sa@<PROJECT_ID>.iam.gserviceaccount.com`) with Compute and Storage permissions
- `gcloud` CLI authenticated, or Application Default Credentials configured

## Setup

### 1. Install dependencies

**Gateway (API server):**

```bash
cd gateway
pip install -r requirements.txt
```

**ML workloads (inference / training):**

```bash
cd code
pip install -r requirements.txt
```

### 2. Configure GCP

Update the following values in `cloud/create_spot_vm.py`, `cloud/cloud_burst_monitor.py`, and `gateway/app.py`:

| Setting      | Default                          | Location                          |
|--------------|----------------------------------|-----------------------------------|
| `PROJECT_ID` | `project-5ca47de0-b0a2-43a7-aed` | `create_spot_vm.py`, `app.py`     |
| `ZONE`       | `us-central1-b`                  | `create_spot_vm.py`, `app.py`     |
| `BUCKET`     | `ai-model-registry-aice`         | `create_spot_vm.py`, `gcs_utils`  |

Ensure `startup.sh` and `shutdown.sh` are accessible from the working directory when `create_spot_vm.py` runs (they are read at VM creation time and embedded as instance metadata).

### 3. Upload a model to GCS

```python
from cloud.gcs_utils import upload_directory

upload_directory(
    bucket_name="ai-model-registry-aice",
    local_path="./my-model-checkpoint",
    gcs_prefix="t5-small/v1.0.0/"
)
```

## Usage

### Local inference

Run inference directly on your machine:

```bash
python code/inference.py \
  --model_path ./models/t5-small \
  --input_text "summarize: The quick brown fox jumps over the lazy dog."
```

### Start the gateway API

```bash
cd gateway
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

**Endpoints:**

| Method | Path      | Description                              |
|--------|-----------|------------------------------------------|
| `GET`  | `/`       | Health check and list of available models|
| `GET`  | `/models` | Full model registry                      |
| `POST` | `/launch` | Provision a Spot VM for a given model    |

**Launch a Spot VM:**

```bash
curl -X POST http://localhost:8080/launch \
  -H "Content-Type: application/json" \
  -d '{"model_name": "t5-small", "zone": "us-central1-b"}'
```

Response:

```json
{
  "message": "Spot VM launched successfully for model: t5-small",
  "vm_name": "spotvm-t5-small-1719234567",
  "status": "provisioning",
  "note": "The VM is starting. Inference server will be available on port 8000 shortly."
}
```

### Automatic cloud burst

Run the resource monitor to burst to a Spot VM when local resources are depleted:

```bash
python cloud/cloud_burst_monitor.py
```

Default thresholds:

- **Memory** > 70%
- **CPU** > 90%

The monitor polls every 60 seconds. When a threshold is crossed, it calls `create_spot_vm` and exits.

### GCS utilities

`cloud/gcs_utils.py` provides three model access patterns:

- **`upload_directory`** — Upload a local checkpoint directory to GCS.
- **`download_model_from_gcs`** — Download a full model folder to local disk.
- **`load_model_from_gcs_streaming`** — Stream weights directly into RAM (memory-efficient for large models).

## Spot VM Configuration

Each Spot VM is provisioned with:

| Setting            | Value                                      |
|--------------------|--------------------------------------------|
| Machine type       | `n2-standard-8`                            |
| Disk               | 200 GB `pd-ssd`                            |
| OS image           | Debian 12 (`debian-cloud`)                 |
| Provisioning model | `SPOT` (preemptible)                       |
| Network tier       | `PREMIUM`                                  |
| Inference port     | `8000`                                     |

**Startup sequence** (`startup.sh`):

1. Read `BUCKET`, `MODEL_PREFIX`, and `MODEL_NAME` from instance metadata.
2. Wait for outbound network connectivity.
3. Download the model from GCS with `gsutil`.
4. Install Python, PyTorch, Transformers, and Safetensors.
5. Start a file server on port 8000 (inference endpoint placeholder).

**Shutdown sequence** (`shutdown.sh`):

On preemption, any checkpoints under `/opt/ml/checkpoints/` are uploaded to `gs://<BUCKET>/checkpoints/<timestamp>/`.

## Roadmap

- [ ] `gateway/spot_vm_manager.py` — VM lifecycle management (list, terminate, health checks)
- [ ] `code/train.py` — Distributed training with checkpoint upload on preemption
- [ ] `local/local_test.py` — End-to-end local integration tests
- [ ] vLLM engine support for Llama 3, Qwen 2.5, and DeepSeek models
- [ ] Replace port-8000 file server with a proper FastAPI inference endpoint on the VM
- [ ] Dynamic input text and request routing from gateway to running VMs

## License

This project is provided as-is for research and development purposes.