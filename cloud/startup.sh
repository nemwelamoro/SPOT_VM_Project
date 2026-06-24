#!/bin/bash
set +e

echo "=== Spot VM Inference Server Starting ==="

# Read metadata
BUCKET=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/BUCKET)
MODEL_PREFIX=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/MODEL_PREFIX)
MODEL_NAME=$(curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/MODEL_NAME)

MODEL_DIR="/models/${MODEL_NAME}"
mkdir -p "$MODEL_DIR"

# Network validation loop (from your working script)
echo "Checking outbound network..."
for i in {1..15}; do
  if curl -s --connect-timeout 3 https://google.com > /dev/null; then
    echo "✅ Internet available."
    break
  else
    echo "⏳ Waiting for network... ($i/15)"
    sleep 3
  fi
done

echo "Downloading model from GCS..."
gsutil -m cp -r "gs://${BUCKET}/${MODEL_PREFIX}*" "$MODEL_DIR/"

echo "Installing Python packages..."
apt-get update -y -q
apt-get install -y python3-pip python3-venv -q

pip3 install --upgrade pip --break-system-packages -q
pip3 install torch transformers safetensors --break-system-packages -q

echo "Starting inference server on port 8000..."
python3 -m http.server 8000 --directory "$MODEL_DIR" &