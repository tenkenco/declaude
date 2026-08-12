# Gateway: Cloud Run service reaching the internal LB via Direct VPC egress.

resource "google_artifact_registry_repository" "images" {
  location      = var.region
  repository_id = "declaude"
  format        = "DOCKER"
}

resource "google_service_account" "gateway" {
  account_id   = "gateway-sa"
  display_name = "declaude gateway"
}

resource "google_project_iam_member" "gateway_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_firestore_database" "main" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# Secrets (values are set out-of-band, never in Terraform state)
resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(["clerk-secret-key", "stripe-secret-key", "stripe-webhook-secret", "stripe-payment-link"])
  secret_id = each.key
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "gateway_access" {
  for_each  = google_secret_manager_secret.secrets
  secret_id = each.value.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.gateway.email}"
}

resource "google_cloud_run_v2_service" "gateway" {
  name                = "declaude-gateway"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = false

  template {
    service_account = google_service_account.gateway.email

    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc.id
        subnetwork = google_compute_subnetwork.main.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }

    scaling {
      min_instance_count = 1 # always-warm: no cold starts for first user
      max_instance_count = 10
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/declaude/gateway:latest"

      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }

      env {
        name  = "DECLAUDE_MODEL_BASE_URL"
        value = "http://${google_compute_address.vllm_ilb.address}/v1"
      }
      env {
        name  = "DECLAUDE_MODEL_NAME"
        value = var.model_served_name
      }
      env {
        name  = "DECLAUDE_FREE_TIER_MONTHLY_LIMIT"
        value = tostring(var.free_tier_monthly_limit)
      }
      env {
        name  = "DECLAUDE_USAGE_BACKEND"
        value = "firestore"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "CLERK_JWKS_URL"
        value = var.clerk_jwks_url
      }
      env {
        name = "STRIPE_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["stripe-secret-key"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "STRIPE_WEBHOOK_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["stripe-webhook-secret"].secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "DECLAUDE_STRIPE_PAYMENT_LINK"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.secrets["stripe-payment-link"].secret_id
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 2
        period_seconds        = 3
        failure_threshold     = 10
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.gateway_access]

  lifecycle {
    # CI (gcloud run deploy) owns the image and adds a service-level scaling block;
    # Terraform must not fight it on every plan.
    ignore_changes = [template[0].containers[0].image, scaling, client, client_version]
  }
}

resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.gateway.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers" # auth enforced in-app via Clerk
}
