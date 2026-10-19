# Backward-compatible example. Prefer bootstrap.tfvars.example for the first
# apply and production.tfvars.example for the Cloud SQL cutover.
project_id                = "clouddetctapi-demo"
region                    = "asia-east1"
container_image           = "us-docker.pkg.dev/cloudrun/container/hello"
cloud_sql_connection_name = ""
public_base_url           = ""
attach_runtime_secrets    = false
scheduler_paused          = true
github_repository         = "bestlatte/CloudDetectApi"

