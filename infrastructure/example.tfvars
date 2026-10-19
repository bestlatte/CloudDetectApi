project_id                = "clouddetctapi-demo"
region                    = "asia-east1"
container_image           = "asia-east1-docker.pkg.dev/clouddetctapi-demo/cloudpulse/cloudpulse:BOOTSTRAP_SHA"
cloud_sql_connection_name = "clouddetctapi-demo:asia-east1:CLOUD_SQL_INSTANCE"
public_base_url           = "https://cloudpulse-web-HASH-de.a.run.app"
attach_runtime_secrets    = true
scheduler_paused          = true
github_repository         = "OWNER/REPOSITORY"

