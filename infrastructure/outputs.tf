output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.cloudpulse.repository_id}"
}

output "web_url" {
  value = google_cloud_run_v2_service.web.uri
}

output "monitor_job_name" {
  value = google_cloud_run_v2_job.monitor.name
}

output "initialize_job_name" {
  value = google_cloud_run_v2_job.initialize.name
}

output "wif_provider" {
  value = var.github_repository == "" ? null : google_iam_workload_identity_pool_provider.github[0].name
}

output "deploy_service_account" {
  value = var.github_repository == "" ? null : google_service_account.deploy[0].email
}

output "bootstrap_next_step" {
  value = var.public_base_url == "" ? "Set public_base_url to web_url before initialization." : "Public base URL configured."
}

