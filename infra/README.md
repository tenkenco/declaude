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

## Alert email

`alert_email` has no default and is deliberately not in source. Export it before any plan or apply:

```bash
export TF_VAR_alert_email=ops@example.com
```

It used to default to `""`. That meant a plan run without it proposed setting the notification
channel's address to `null`, so an apply would have switched off ops alerting silently. A missing
value is now an error.

## Testing a provider upgrade

There is no staging project. `plan-provider-upgrade.sh` is the cheap substitute: it copies prod
state to a scratch prefix, plans the given ref against the copy, prints the diff, and deletes the
scratch. Plan is read-only against GCP, and using copied state means prod state cannot be rewritten
by a state-schema upgrade during refresh.

```bash
gcloud auth application-default login
export TF_VAR_alert_email=ops@example.com
./plan-provider-upgrade.sh <git-ref>      # exit 0 = zero diff, 2 = diff printed
```

Always run it against `main` as well, so you can tell a diff the upgrade caused from drift that was
already there. That control is what showed the hashicorp/google 7.x bump was clean.
