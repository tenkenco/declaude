resource "google_compute_network" "vpc" {
  name                    = "declaude-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "main" {
  name          = "declaude-subnet"
  network       = google_compute_network.vpc.id
  region        = var.region
  ip_cidr_range = "10.10.0.0/24"
}

# Proxy-only subnet required by the internal L7 load balancer.
resource "google_compute_subnetwork" "proxy_only" {
  name          = "declaude-proxy-only"
  network       = google_compute_network.vpc.id
  region        = var.region
  ip_cidr_range = "10.10.1.0/24"
  purpose       = "REGIONAL_MANAGED_PROXY"
  role          = "ACTIVE"
}

# Egress for model download (HF) via Cloud NAT; model VMs have no public IPs.
resource "google_compute_router" "nat_router" {
  name    = "declaude-nat-router"
  network = google_compute_network.vpc.id
  region  = var.region
}

resource "google_compute_router_nat" "nat" {
  name                               = "declaude-nat"
  router                             = google_compute_router.nat_router.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

resource "google_compute_firewall" "allow_lb_to_vllm" {
  name    = "allow-lb-to-vllm"
  network = google_compute_network.vpc.id
  allow {
    protocol = "tcp"
    ports    = ["8000"]
  }
  # proxy-only subnet + health checkers
  source_ranges = ["10.10.1.0/24", "130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["vllm"]
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = google_compute_network.vpc.id
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
  source_ranges = ["35.235.240.0/20"] # IAP range only; no public SSH
  target_tags   = ["vllm"]
}
