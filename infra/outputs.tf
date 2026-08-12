output "gateway_url" {
  value = google_cloud_run_v2_service.gateway.uri
}

output "vllm_internal_lb_ip" {
  value = google_compute_address.vllm_ilb.address
}

output "artifact_repo" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/declaude"
}

output "wif_provider" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_sa" {
  value = google_service_account.deployer.email
}
