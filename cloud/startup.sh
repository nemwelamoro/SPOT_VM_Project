#!/bin/bash
set +e

echo "=============================================="
echo "=== Optimized Dynamic Cloud Burst Started  ==="
echo "=============================================="

# 1. System Level Optimization: Run directly as root
sysctl -w net.core.rmem_max=134217728 > /dev/null 2>&1
sysctl -w net.core.wmem_max=134217728 > /dev/null 2>&1
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864" > /dev/null 2>&1
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864" > /dev/null 2>&1

# 2. Network validation loop
echo "Checking outbound network route..."
for i in {1..15}; do
  if curl -s --connect-timeout 3 https://google.com > /dev/null; then
    echo "✅ Internet and DNS paths online."
    break
  else
    echo "⏳ Network path unreachable, retrying... ($i/15)"
    sleep 2
  fi
done

# 3. Read instance metadata values using the working UPPERCASE attributes layout
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
BUCKET=$(curl -s -H "Metadata-Flavor: Google" "$METADATA_URL/BUCKET")
MODEL_PREFIX=$(curl -s -H "Metadata-Flavor: Google" "$METADATA_URL/MODEL_PREFIX")
INPUT_TEXT=$(curl -s -H "Metadata-Flavor: Google" "$METADATA_URL/INPUT_TEXT")

echo "--> Extracted BUCKET: $BUCKET"
echo "--> Extracted MODEL_PREFIX: $MODEL_PREFIX"

# Validation stop block
if [ -z "$BUCKET" ] || [ -z "$MODEL_PREFIX" ]; then
  echo "❌ Error: Variable parsing failed. Attributes mapping came up empty."
  exit 1
fi

MODEL_LOCAL_DIR="/opt/ml/model"
CODE_LOCAL_DIR="/opt/ml/code"

echo "[1/5] Creating directories..."
mkdir -p "$MODEL_LOCAL_DIR"
mkdir -p "/opt/ml"

# Install core python dependency components
apt-get update -y -q && apt-get install -y python3-pip -y python3-venv -q

echo ""
echo "[2/5] Fetching runtime execution code..."
gsutil -m cp -r "gs://${BUCKET}/code" "/opt/ml/"
if [ $? -ne 0 ]; then
  echo "❌ Error: Failed to download code directory from GCS."
  exit 1
fi
echo "✅ Code runtime directory synchronized."

echo ""
echo "[3/5] Launching Concurrently: Dependencies & Model Weights..."

# ASYNC TASK 1: Run package installation in background thread
(
  echo "--> [Background] Starting pip install pipeline..."
  pip3 install --upgrade pip -q --break-system-packages
  if [ -f "$CODE_LOCAL_DIR/requirements.txt" ]; then
    pip3 install -r "$CODE_LOCAL_DIR/requirements.txt" --no-cache-dir -q --break-system-packages
  fi
  echo "--> [Background] Pip dependencies completed successfully."
) &
PIP_PID=$!

# ASYNC TASK 2: High-throughput multithreaded weight extraction
echo "--> [Main Thread] Downloading heavy model artifacts..."
gsutil -m cp -r "gs://${BUCKET}/${MODEL_PREFIX}*" "$MODEL_LOCAL_DIR/"
if [ $? -ne 0 ]; then
  echo "❌ Error: Failed to download model weights from GCS."
  exit 1
fi
echo "--> [Main Thread] Model weight download complete."

echo ""
echo "[4/5] Synchronizing asynchronous tasks..."
wait $PIP_PID
echo "✅ Pipeline states matched. Environment is ready."

echo ""
echo "[5/5] Running inference engine..."
export PYTHONDONTWRITEBYTECODE=1

python3 "$CODE_LOCAL_DIR/inference.py" \
    --model_path "$MODEL_LOCAL_DIR" \
    --input_text "$INPUT_TEXT" \
    --max_length 120

echo ""
echo "=============================================="
echo "=== Inference completed successfully       ==="
echo "=============================================="
