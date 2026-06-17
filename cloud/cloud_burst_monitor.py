import psutil
import time
from create_spot_vm import create_spot_vm

# ==================== CONFIGURATION ====================
PROJECT_ID = "project-5ca47de0-b0a2-43a7-aed"                   
ZONE = "us-central1-a"                            
BUCKET = "ai-model-registry-aice"                 
MODEL_PREFIX = "t5-small/v1.0.0/"                 

# Example input for inference (you can make this dynamic later)
DEFAULT_INPUT_TEXT = "summarize: The quick brown fox jumps over the lazy dog. It was a sunny day in the park."

def resources_depleted(mem_threshold=70, cpu_threshold=90):
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=2)
    print(f"Memory: {mem.percent}% | CPU: {cpu}%")
    return mem.percent > mem_threshold or cpu > cpu_threshold

def main():
    while True:
        if resources_depleted():
            print("\n🚨 Local resources depleted → Bursting to Spot VM Creationfor inference...")

            instance_name = f"t5-inference-burst-{int(time.time())}"

            create_spot_vm(
                project_id=PROJECT_ID,
                zone=ZONE,
                instance_name=instance_name,
                bucket=BUCKET,
                model_prefix=MODEL_PREFIX,
                input_text=DEFAULT_INPUT_TEXT
            )
            break  # Stop monitoring after bursting (you can change this later)
        time.sleep(60)

if __name__ == "__main__":
    main()