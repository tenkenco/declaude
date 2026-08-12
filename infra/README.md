# declaude infrastructure

Terraform for the dedicated `declaude-prod` GCP project.

## Topology
- **Model tier**: vLLM (Qwen2.5-32B-Instruct-AWQ) on an L4 GPU MIG, private IPs only,
  egress via Cloud NAT, fronted by an internal L7 load balancer at 10.10.0.100.
- **Gateway**: Cloud Run (public), reaches the ILB via Direct VPC egress. Clerk auth,
  Firestore usage metering, Stripe billing. `/healthz` note: GFE reserves it on run.app — use `/health`.
- **CI/CD**: GitHub Actions deploys via Workload Identity Federation (`github-deployer` SA, no keys).
- **State**: gs://declaude-prod-tfstate (versioned).

## Secrets (Secret Manager, values set out-of-band)
clerk-secret-key, stripe-secret-key, stripe-webhook-secret, stripe-payment-link

## Scaling up
Bump `model_machine_type` to g2-standard-24 + `model_accelerator.count=2` (needs quota),
or raise `model_replicas` — the ILB spreads load across MIG instances.
