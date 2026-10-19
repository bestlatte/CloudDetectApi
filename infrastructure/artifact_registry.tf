resource "google_artifact_registry_repository" "cloudpulse" {
  location      = var.region
  repository_id = local.registry_name
  description   = "Versioned CloudPulse web and monitor images"
  format        = "DOCKER"
  labels        = local.common_labels

  depends_on = [google_project_service.required]
}

