resource "google_secret_manager_secret" "database_url" {
  secret_id = "cloudpulse-database-url"
  labels    = local.common_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret" "admin_password_hash" {
  secret_id = "cloudpulse-admin-password-hash"
  labels    = local.common_labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.required]
}

# Secret versions are intentionally absent. Add values through the Console or
# gcloud after explicit approval so plaintext never enters Terraform state.

