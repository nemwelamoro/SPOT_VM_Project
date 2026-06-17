# cloud/gcs_utils.py
from google.cloud import storage
import os
import json
import torch
from transformers import AutoConfig, AutoTokenizer, AutoModelForSeq2SeqLM
from safetensors.torch import load as load_safetensors
import io

def upload_directory(bucket_name: str, local_path: str, gcs_prefix: str):
    """Upload a local directory to GCS (useful for checkpoints later)."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for root, _, files in os.walk(local_path):
        for file in files:
            local_file = os.path.join(root, file)
            relative_path = os.path.relpath(local_file, local_path)
            gcs_blob_path = os.path.join(gcs_prefix, relative_path).replace("\\", "/")

            blob = bucket.blob(gcs_blob_path)
            blob.upload_from_filename(local_file)
            print(f"Uploaded {file} → gs://{bucket_name}/{gcs_blob_path}")


def download_model_from_gcs(bucket_name: str, gcs_prefix: str, local_dir: str):
    """Download entire model folder from GCS to local disk (simple & reliable)."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    os.makedirs(local_dir, exist_ok=True)

    blobs = bucket.list_blobs(prefix=gcs_prefix)
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        relative_path = blob.name[len(gcs_prefix):]
        local_file_path = os.path.join(local_dir, relative_path)
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        blob.download_to_filename(local_file_path)
        print(f"Downloaded {blob.name} → {local_file_path}")


def load_model_from_gcs_streaming(bucket_name: str, gcs_prefix: str):
    """
    Advanced: Stream model directly from GCS into RAM (like your app.py).
    More memory efficient for large models.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Load config
    config_blob = bucket.blob(f"{gcs_prefix}config.json")
    config_dict = json.loads(config_blob.download_as_bytes().decode("utf-8"))
    config = AutoConfig.from_pretrained("t5-small")
    config.update(config_dict)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained("t5-small")

    # Try safetensors first, fallback to pytorch_model.bin
    try:
        weight_blob = bucket.blob(f"{gcs_prefix}model.safetensors")
        state_dict = load_safetensors(weight_blob.download_as_bytes())
    except Exception:
        weight_blob = bucket.blob(f"{gcs_prefix}pytorch_model.bin")
        buffer = io.BytesIO(weight_blob.download_as_bytes())
        state_dict = torch.load(buffer, map_location="cpu")

    model = AutoModelForSeq2SeqLM.from_config(config)
    model.load_state_dict(state_dict, strict=False)
    model.tie_weights()
    model.eval()

    print("✅ Model loaded directly from GCS into RAM")
    return model, tokenizer