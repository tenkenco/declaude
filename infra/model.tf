# vLLM serving tier: GPU MIG behind an internal L7 load balancer.

resource "google_service_account" "vllm" {
  account_id   = "vllm-sa"
  display_name = "vLLM model server"
}

resource "google_compute_instance_template" "vllm" {
  name_prefix  = "vllm-"
  machine_type = var.model_machine_type
  region       = var.region
  tags         = ["vllm"]

  disk {
    source_image = "projects/cos-cloud/global/images/family/cos-stable"
    boot         = true
    disk_size_gb = 150
    disk_type    = "pd-ssd"
  }

  guest_accelerator {
    type  = var.model_accelerator.type
    count = var.model_accelerator.count
  }

  scheduling {
    on_host_maintenance = "TERMINATE"
    automatic_restart   = true
  }

  network_interface {
    subnetwork = google_compute_subnetwork.main.id
    # no access_config: private IP only, egress via Cloud NAT
  }

  service_account {
    email  = google_service_account.vllm.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    user-data = templatefile("${path.module}/templates/vllm-cloud-init.yaml", {
      model_hf_id       = var.model_hf_id
      model_served_name = var.model_served_name
      max_model_len     = var.vllm_max_model_len
      tensor_parallel   = var.model_accelerator.count
    })
    google-logging-enabled = "true"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_health_check" "vllm" {
  name                = "vllm-health"
  check_interval_sec  = 15
  timeout_sec         = 10
  healthy_threshold   = 2
  unhealthy_threshold = 6
  http_health_check {
    port         = 8000
    request_path = "/health"
  }
}

resource "google_compute_region_instance_group_manager" "vllm" {
  name               = "vllm-mig"
  region             = var.region
  base_instance_name = "vllm"
  target_size        = var.model_replicas

  distribution_policy_zones = [var.zone]

  version {
    instance_template = google_compute_instance_template.vllm.id
  }

  named_port {
    name = "http"
    port = 8000
  }

  auto_healing_policies {
    health_check      = google_compute_health_check.vllm.id
    initial_delay_sec = 1800 # model download + load can take a while on first boot
  }

  update_policy {
    type                  = "PROACTIVE"
    minimal_action        = "REPLACE"
    max_surge_fixed       = 0
    max_unavailable_fixed = 3
  }
}

# Internal L7 LB in front of the MIG.
resource "google_compute_region_backend_service" "vllm" {
  name                  = "vllm-backend"
  region                = var.region
  protocol              = "HTTP"
  load_balancing_scheme = "INTERNAL_MANAGED"
  timeout_sec           = 300
  port_name             = "http"
  health_checks         = [google_compute_health_check.vllm.id]

  backend {
    group           = google_compute_region_instance_group_manager.vllm.instance_group
    balancing_mode  = "UTILIZATION"
    capacity_scaler = 1.0
  }
}

resource "google_compute_region_url_map" "vllm" {
  name            = "vllm-urlmap"
  region          = var.region
  default_service = google_compute_region_backend_service.vllm.id
}

resource "google_compute_region_target_http_proxy" "vllm" {
  name    = "vllm-proxy"
  region  = var.region
  url_map = google_compute_region_url_map.vllm.id
}

resource "google_compute_address" "vllm_ilb" {
  name         = "vllm-ilb-ip"
  region       = var.region
  subnetwork   = google_compute_subnetwork.main.id
  address_type = "INTERNAL"
  address      = "10.10.0.100"
}

resource "google_compute_forwarding_rule" "vllm" {
  name                  = "vllm-ilb"
  region                = var.region
  load_balancing_scheme = "INTERNAL_MANAGED"
  network               = google_compute_network.vpc.id
  subnetwork            = google_compute_subnetwork.main.id
  ip_address            = google_compute_address.vllm_ilb.id
  port_range            = "80"
  target                = google_compute_region_target_http_proxy.vllm.id
  depends_on            = [google_compute_subnetwork.proxy_only]
}
