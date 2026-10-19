resource "google_service_account" "runtime" {
  account_id   = "cloudpulse-runtime"
  display_name = "CloudPulse runtime"
}

resource "google_service_account" "scheduler" {
  account_id   = "cloudpulse-scheduler"
  display_name = "CloudPulse scheduler invoker"
}

resource "google_service_account" "deploy" {
  count        = var.github_repository == "" ? 0 : 1
  account_id   = "cloudpulse-deploy"
  display_name = "CloudPulse GitHub deployment"
}

resource "google_project_iam_member" "runtime_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_database_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "runtime_admin_hash" {
  secret_id = google_secret_manager_secret.admin_password_hash.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "deploy_registry" {
  count   = var.github_repository == "" ? 0 : 1
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deploy[0].email}"
}

resource "google_project_iam_member" "deploy_run" {
  count   = var.github_repository == "" ? 0 : 1
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.deploy[0].email}"
}

resource "google_service_account_iam_member" "deploy_act_as_runtime" {
  count              = var.github_repository == "" ? 0 : 1
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deploy[0].email}"
}

