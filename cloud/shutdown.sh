#!/bin/bash
echo "Preemption detected. Saving any work..."
# Add checkpoint upload logic here later when we add training
gsutil -m cp -r /opt/ml/checkpoints/* "gs://${BUCKET}/checkpoints/$(date +%s)/" || true
echo "Shutdown complete."