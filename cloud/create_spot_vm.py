# cloud/create_spot_vm.py
from google.cloud import compute_v1

def create_spot_vm(
    project_id: str,
    zone: str,
    instance_name: str,
    bucket: str,
    model_prefix: str,
    input_text: str
):
    client = compute_v1.InstancesClient()
    image_client = compute_v1.ImagesClient()

    image = image_client.get_from_family(project="debian-cloud", family="debian-12")

    disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image=image.self_link,
            disk_size_gb=100,
            disk_type=f"zones/{zone}/diskTypes/pd-balanced",
        ),
    )

    # ✅ Use strings (most compatible way)
    scheduling = compute_v1.Scheduling(
        provisioning_model="SPOT",
        instance_termination_action="STOP"
    )

    metadata = compute_v1.Metadata(items=[
        {"key": "startup-script", "value": open("startup.sh").read()},
        {"key": "shutdown-script", "value": open("shutdown.sh").read()},
        {"key": "BUCKET", "value": bucket},
        {"key": "MODEL_PREFIX", "value": model_prefix},
        {"key": "INPUT_TEXT", "value": input_text},
    ])

    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{zone}/machineTypes/n1-standard-8",
        disks=[disk],
        network_interfaces=[compute_v1.NetworkInterface(network="global/networks/default")],
        scheduling=scheduling,
        metadata=metadata,
        service_accounts=[{
            "email": f"slm-spot-vm-sa@{project_id}.iam.gserviceaccount.com",
            "scopes": ["https://www.googleapis.com/auth/cloud-platform"]
        }],
        labels={"purpose": "slm-inference-burst", "model": "t5-small"},
    )

    print(f"Creating Spot VM: {instance_name} in {zone}...")
    operation = client.insert(project=project_id, zone=zone, instance_resource=instance)
    operation.result(timeout=300)
    print(f"✅ Spot VM {instance_name} created successfully!")