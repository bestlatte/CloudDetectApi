variable "project_id" {
  description = "Google Cloud project that owns the Terraform state bucket."
  type        = string
  default     = "clouddetctapi-demo"
}

variable "location" {
  description = "Cloud Storage location for Terraform state."
  type        = string
  default     = "asia-east1"
}

variable "state_bucket_name" {
  description = "Globally unique Cloud Storage bucket name for Terraform state."
  type        = string
  default     = "clouddetctapi-demo-cloudpulse-tfstate"

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "state_bucket_name must be a valid Cloud Storage bucket name."
  }
}
