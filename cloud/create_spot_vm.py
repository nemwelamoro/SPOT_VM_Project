# cloud/create_spot_vm.py
from google.cloud import compute_v1
import time

def create_spot_vm(
    project_id: str,
    zone: str,
    bucket: str,
    model_prefix: str,
    input_text: str,
    instance_name: str = None
):
    if instance_name is None:
        instance_name = f"t5-inference-burst-{int(time.time())}"

    client = compute_v1.InstancesClient()
    image_client = compute_v1.ImagesClient()

    image = image_client.get_from_family(project="debian-cloud", family="debian-12")

    disk = compute_v1.AttachedDisk(
        boot=True,
        auto_delete=True,
        initialize_params=compute_v1.AttachedDiskInitializeParams(
            source_image=image.self_link,
            disk_size_gb=200,
            disk_type=f"zones/{zone}/diskTypes/pd-ssd",
        ),
    )

    scheduling = compute_v1.Scheduling(
        provisioning_model="SPOT",
        instance_termination_action="STOP"
    )
      # OPTIMIZATION 2: Enable Tier 1 network performance for faster networking pipes
    #network_performance_config = compute_v1.NetworkPerformanceConfig(
        #total_egress_bandwidth_tier="TIER_1"
    #)

    instance = compute_v1.Instance(
        name=instance_name,
        machine_type=f"zones/{zone}/machineTypes/n2-standard-8",
        disks=[disk],
        #network_performance_config=network_performance_config,
        network_interfaces=[compute_v1.NetworkInterface(network="global/networks/default", access_configs=[compute_v1.AccessConfig(
                name="External NAT",
                type_="ONE_TO_ONE_NAT",
                network_tier="PREMIUM"
            )])],
        scheduling=scheduling,
        metadata=compute_v1.Metadata(items=[
            {"key": "startup-script", "value": open("startup.sh", encoding="utf-8").read()},
            {"key": "shutdown-script", "value": open("shutdown.sh", encoding="utf-8").read()},
            {"key": "BUCKET", "value": bucket},
            {"key": "MODEL_PREFIX", "value": model_prefix},
            {"key": "INPUT_TEXT", "value": input_text},
        ]),
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