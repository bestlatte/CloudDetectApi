locals {
  secret_environment = {
    DATABASE_URL        = google_secret_manager_secret.database_url.secret_id
    ADMIN_PASSWORD_HASH = google_secret_manager_secret.admin_password_hash.secret_id
  }
}

resource "google_cloud_run_v2_service" "web" {
  name                = local.service_name
  location            = var.region
  deletion_protection = false
  labels              = local.common_labels

  template {
    service_account = google_service_account.runtime.email
    timeout         = "60s"
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    containers {
      image = var.container_image
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "COMMIT_SHA"
        value = "terraform-bootstrap"
      }
      dynamic "env" {
        for_each = var.public_base_url == "" ? [] : [var.public_base_url]
        content {
          name  = "PUBLIC_BASE_URL"
          value = env.value
        }
      }
      dynamic "env" {
        for_each = var.attach_runtime_secrets ? local.secret_environment : {}
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }
      dynamic "volume_mounts" {
        for_each = var.cloud_sql_connection_name == "" ? [] : [1]
        content {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }
    }
    dynamic "volumes" {
      for_each = var.cloud_sql_connection_name == "" ? [] : [1]
      content {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.cloud_sql_connection_name]
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "public_read" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_job" "monitor" {
  name                = local.monitor_job
  location            = var.region
  deletion_protection = false
  labels              = local.common_labels

  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.runtime.email
      timeout         = "300s"
      max_retries     = 1
      containers {
        image   = var.container_image
        command = ["python", "-m", "app.jobs.run_monitor"]
        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
        env {
          name  = "ENVIRONMENT"
          value = "production"
        }
        dynamic "env" {
          for_each = var.public_base_url == "" ? [] : [var.public_base_url]
          content {
            name  = "PUBLIC_BASE_URL"
            value = env.value
          }
        }
        dynamic "env" {
          for_each = var.attach_runtime_secrets ? { DATABASE_URL = google_secret_manager_secret.database_url.secret_id } : {}
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
        dynamic "volume_mounts" {
          for_each = var.cloud_sql_connection_name == "" ? [] : [1]
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }
      }
      dynamic "volumes" {
        for_each = var.cloud_sql_connection_name == "" ? [] : [1]
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = [var.cloud_sql_connection_name]
          }
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image]
  }
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_job" "initialize" {
  name                = local.init_job
  location            = var.region
  deletion_protection = false
  labels              = local.common_labels

  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.runtime.email
      timeout         = "300s"
      max_retries     = 0
      containers {
        image   = var.container_image
        command = ["python", "-m", "app.db.initialize"]
        env {
          name  = "ENVIRONMENT"
          value = "production"
        }
        dynamic "env" {
          for_each = var.public_base_url == "" ? [] : [var.public_base_url]
          content {
            name  = "PUBLIC_BASE_URL"
            value = env.value
          }
        }
        dynamic "env" {
          for_each = var.attach_runtime_secrets ? { DATABASE_URL = google_secret_manager_secret.database_url.secret_id } : {}
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }
        dynamic "volume_mounts" {
          for_each = var.cloud_sql_connection_name == "" ? [] : [1]
          content {
            name       = "cloudsql"
            mount_path = "/cloudsql"
          }
        }
      }
      dynamic "volumes" {
        for_each = var.cloud_sql_connection_name == "" ? [] : [1]
        content {
          name = "cloudsql"
          cloud_sql_instance {
            instances = [var.cloud_sql_connection_name]
          }
        }
      }
    }
  }
  lifecycle {
    ignore_changes = [template[0].template[0].containers[0].image]
  }
  depends_on = [google_project_service.required]
}
