# ~/gateway/create_spot_vm.py
from google.cloud import compute_v1
import time
from model_registry import MODEL_REGISTRY

def create_spot_vm(
    project_id: str,
    zone: str,
    model_name: str,
    bucket: str = "ai-model-registry-aice"
):
    if model_name not in MODEL_REGISTRY:
        raise ValueError(f"Model '{model_name}' not found")

    model_info = MODEL_REGISTRY[model_name]
    model_prefix = model_info["gcs_path"]

    client = compute_v1.InstancesClient()
    image_client = compute_v1.ImagesClient()

    image = image_client.get_from_family(project="debian-cloud", family="debian-12")

    disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image=image.self_link,
            disk_size_gb=200,
            disk_type=f"zones/{zone}/diskTypes/pd-ssd",   # Faster disk
        ),
    )

    scheduling = compute_v1.Scheduling(
        provisioning_model="SPOT",
    )

    instance = compute_v1.Instance(
        name=f"spotvm-{model_name}-{int(time.time())}",
        machine_type=f"zones/{zone}/machineTypes/n2-standard-8",
        disks=[disk],
        network_interfaces=[
            compute_v1.NetworkInterface(
                network="global/networks/default",
                access_configs=[
                    compute_v1.AccessConfig(
                        name="External NAT",
                        type_="ONE_TO_ONE_NAT",
                        network_tier="PREMIUM"           # ← Important for better routing
                    )
                ]
            )
        ],
        scheduling=scheduling,
        metadata=compute_v1.Metadata(items=[
            {"key": "startup-script", "value": open("startup.sh", encoding="utf-8").read()},
            {"key": "shutdown-script", "value": open("shutdown.sh", encoding="utf-8").read()},
            {"key": "BUCKET", "value": bucket},
            {"key": "MODEL_PREFIX", "value": model_prefix},
            {"key": "MODEL_NAME", "value": model_name},
        ]),
        service_accounts=[{
            "email": f"ml-spot-vm-sa@{project_id}.iam.gserviceaccount.com",
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
        }],
        labels={"purpose": "inference-server", "model": model_name},
    )

    print(f"Creating Spot VM for model: {model_name}...")
    operation = client.insert(project=project_id, zone=zone, instance_resource=instance)
    operation.result(timeout=300)
    print(f"✅ Spot VM created successfully!")