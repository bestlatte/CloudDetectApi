variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
  default     = "clouddetctapi-demo"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid Google Cloud project ID."
  }
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

variable "commit_sha" {
  description = "Commit identifier exposed by the deployed Web service. Keep it aligned with container_image."
  type        = string
  default     = "terraform-bootstrap"
}

variable "cloud_sql_connection_name" {
  description = "Existing Cloud SQL connection name (project:region:instance); leave blank during bootstrap."
  type        = string
  default     = ""

  validation {
    condition     = var.cloud_sql_connection_name == "" || can(regex("^[^:]+:[^:]+:[^:]+$", var.cloud_sql_connection_name))
    error_message = "cloud_sql_connection_name must be empty or use project:region:instance format."
  }
}

variable "public_base_url" {
  description = "Deployed Cloud Run URL used by the approved Mock templates; set after the first service creation."
  type        = string
  default     = ""

  validation {
    condition     = var.public_base_url == "" || can(regex("^https://[^/]+/?$", var.public_base_url))
    error_message = "public_base_url must be empty during bootstrap or an HTTPS origin without a path."
  }
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

  validation {
    condition     = var.github_repository == "" || can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must be empty or use exact OWNER/REPOSITORY format."
  }
}

variable "database_secret_version" {
  description = "Secret Manager version for DATABASE_URL. Pin a numeric version in production."
  type        = string
  default     = "latest"

  validation {
    condition     = var.database_secret_version == "latest" || can(regex("^[1-9][0-9]*$", var.database_secret_version))
    error_message = "database_secret_version must be latest or a positive numeric version."
  }
}

variable "admin_password_secret_version" {
  description = "Secret Manager version for ADMIN_PASSWORD_HASH. Pin a numeric version in production."
  type        = string
  default     = "latest"

  validation {
    condition     = var.admin_password_secret_version == "latest" || can(regex("^[1-9][0-9]*$", var.admin_password_secret_version))
    error_message = "admin_password_secret_version must be latest or a positive numeric version."
  }
}

