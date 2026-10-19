provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  service_name  = "cloudpulse-web"
  monitor_job   = "cloudpulse-monitor"
  init_job      = "cloudpulse-initialize"
  registry_name = "cloudpulse"
  common_labels = {
    application = "cloudpulse"
    managed-by  = "terraform"
  }
}

