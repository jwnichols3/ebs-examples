import boto3
from resource_discovery import discover_resources
from alarm_manager import fetch_alarms_status
from dashboard_manager import manage_dashboard
from utils import setup_logging, handle_error, assume_role

logger = setup_logging()


def main():
    # Define the configuration for accounts, regions, and clusters
    accounts = [
        {"id": "357044226454", "role_name": "CrossAccountObservabilityRole"},
        # ... (other accounts)
    ]
    regions = ["us-west-2", "us-east-1"]  # ... (other regions)
    clusters = [
        {"name": "YourClusterName"},
        {"name": "ClusterName2"},
    ]  # ... (other clusters)
    # Define Observability Account ID and Role
    observability_account_id = "161521808930"
    dashboard_manager_role = "CloudWatchDashboardManager"

    for account in accounts:
        for region in regions:
            for cluster in clusters:
                # Assume role in Application account for data gathering
                app_session = assume_role(
                    account["id"], "CrossAccountObservabilityRole", region
                )

                # Discover Resources and Fetch Alarms Status
                instances, volumes = discover_resources(
                    account["id"],
                    "CrossAccountObservabilityRole",
                    region,
                    cluster["name"],
                )
                resources = {"Instances": instances, "Volumes": volumes}
                print(f"Resource count: EC2 {len(instances)} + EBS {len(volumes)}")
                alarms_status = fetch_alarms_status(app_session, resources)

                # Assume role in Observability account for dashboard management
                obs_session = assume_role(
                    observability_account_id, dashboard_manager_role, region
                )

                # Create/Update Dashboard
                response = manage_dashboard(
                    account_id=observability_account_id,
                    role_name=dashboard_manager_role,
                    region=region,
                    cluster_name=cluster["name"],
                    instances=instances,
                    volumes=volumes,
                    alarms_status=alarms_status,
                    session=obs_session,
                )
                print(f'Dashboard Response for {cluster["name"]}: {response}')


if __name__ == "__main__":
    main()
