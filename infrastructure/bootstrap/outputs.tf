output "state_bucket_name" {
  value       = google_storage_bucket.terraform_state.name
  description = "Bucket to place in the main backend.hcl file."
}
