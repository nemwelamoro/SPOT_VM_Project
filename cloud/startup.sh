#!/bin/bash
set -e

echo "=== Spot VM Cloud Burst Started ==="

# Read metadata passed from create_spot_vm.py
BUCKET=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/BUCKET)
MODEL_PREFIX=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/MODEL_PREFIX)
INPUT_TEXT=$(curl -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/attributes/INPUT_TEXT)

MODEL_LOCAL_DIR="/opt/ml/model"
mkdir -p $MODEL_LOCAL_DIR

echo "Downloading model from gs://${BUCKET}/${MODEL_PREFIX} ..."
gsutil -m cp -r "gs://${BUCKET}/${MODEL_PREFIX}*" $MODEL_LOCAL_DIR/

echo "Running inference..."
cd /opt/ml
python3 -m pip install --upgrade pip -q
pip install -r /opt/ml/code/requirements.txt -q

python3 /opt/ml/code/inference.py \
    --model_path "$MODEL_LOCAL_DIR" \
    --input_text "$INPUT_TEXT" \
    --max_length 120

echo "=== Inference completed successfully ==="