variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
  default     = "clouddetctapi-demo"
}

variable "region" {
  description = "Regional location for Cloud Run, Scheduler and Artifact Registry."
  type        = string
  default     = "asia-east1"
}

variable "container_image" {
  description = "Bootstrap or released container image. CD owns later image revisions."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cloud_sql_connection_name" {
  description = "Existing Cloud SQL connection name (project:region:instance); leave blank during bootstrap."
  type        = string
  default     = ""
}

variable "public_base_url" {
  description = "Deployed Cloud Run URL used by the approved Mock templates; set after the first service creation."
  type        = string
  default     = ""
}

variable "attach_runtime_secrets" {
  description = "Attach latest Secret Manager values only after operators have created secret versions."
  type        = bool
  default     = false
}

variable "scheduler_paused" {
  description = "Keep true until DB initialization and a successful manual Monitor Job run."
  type        = bool
  default     = true
}

variable "github_repository" {
  description = "Exact owner/repository for GitHub OIDC. Empty disables WIF resources."
  type        = string
  default     = ""
}

