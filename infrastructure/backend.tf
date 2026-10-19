terraform {
  # The bucket and prefix are supplied at init time through backend.hcl.
  # Keeping values out of source lets the same configuration be reused safely.
  backend "gcs" {}
}
