# GitHub Actions -> GCP via Workload Identity Federation (no long-lived keys).

resource "google_service_account" "deployer" {
  account_id   = "github-deployer"
  display_name = "GitHub Actions deployer"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${var.github_repo}\""
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Scoped by subject, not by repository. A repository-wide principalSet let any workflow in the
# repository impersonate this account, including one added by a pull request.
#
# The deploy job names the production environment, so GitHub sets the subject to
# "environment:production". That one subject is the whole allowance. A pull request job
# carries "pull_request", and a job on main without an environment carries
# "ref:refs/heads/main". Neither one matches.
#
# The deploy job in .github/workflows/deploy.yml must keep its "environment: production"
# line. Remove that line and GitHub sends a different subject, and the deploy loses access.
resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/subject/repo:${var.github_repo}:environment:production"
}

resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/run.developer",
    "roles/artifactregistry.writer",
    "roles/iam.serviceAccountUser",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# --- Pull request plans ---------------------------------------------------
# A second identity, read-only. The Terraform plan on every infra pull request runs as this
# service account. It reads the project to refresh state, and it reads the state bucket. It
# holds no write permission anywhere, so plans must run with -lock=false. Pull request jobs
# reach this account and no other, because every binding below is scoped by subject.

resource "google_service_account" "planner" {
  account_id   = "github-planner"
  display_name = "GitHub Actions Terraform planner (read-only)"
}

# Pull request jobs only. A push to main carries a different subject and cannot use this
# account, so the plan identity exists on pull requests and nowhere else.
resource "google_service_account_iam_member" "planner_wif" {
  service_account_id = google_service_account.planner.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/subject/repo:${var.github_repo}:pull_request"
}

# viewer reads the resources. securityReviewer reads the IAM policies, which viewer does not
# cover, and this configuration manages four kinds of IAM member. Both are read-only.
resource "google_project_iam_member" "planner_roles" {
  for_each = toset(["roles/viewer", "roles/iam.securityReviewer"])
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.planner.email}"
}

# objectViewer reads the state file. legacyBucketReader reads the bucket metadata that the
# GCS backend asks for at init. Both are read-only.
resource "google_storage_bucket_iam_member" "planner_state" {
  for_each = toset(["roles/storage.objectViewer", "roles/storage.legacyBucketReader"])
  bucket   = var.tfstate_bucket
  role     = each.key
  member   = "serviceAccount:${google_service_account.planner.email}"
}
