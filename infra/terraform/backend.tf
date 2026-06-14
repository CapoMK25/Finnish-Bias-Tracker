terraform {
  backend "gcs" {
    bucket = "fbt-backups-a750fecc8f454b61"
    prefix = "terraform/state"                 # An isolated folder path for the state file
  }
}