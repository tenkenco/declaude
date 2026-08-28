# declaude infrastructure

Terraform for the dedicated `declaude-prod` GCP project.

## Topology
- **Model tier**: vLLM (Qwen2.5-32B-Instruct-AWQ) on an L4 GPU MIG, private IPs only,
  egress via Cloud NAT, fronted by an internal L7 load balancer at 10.10.0.100.
- **Gateway**: Cloud Run (public), reaches the ILB via Direct VPC egress. Clerk auth,
  Firestore usage metering, Stripe billing. `/healthz` note: GFE reserves it on run.app — use `/health`.
- **CI/CD**: GitHub Actions deploys via Workload Identity Federation (`github-deployer` SA, no keys).
  Pull requests plan through a second, read-only identity (`github-planner` SA).
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

## Plans on pull requests

`.github/workflows/terraform-plan.yml` runs `terraform plan` on every pull request that
touches `infra/`. It posts one comment, which it rewrites on each push. The comment counts
the create, update, replace and destroy operations. It then names every resource Terraform
would destroy or replace.

A plan with no destroy or replace passes. A plan with either one fails the check. Add the
`infra:destroy-ok` label to the pull request to accept the destroy, and the check reruns and
passes.

The label is self-serve. The author can add it, so the label records a decision, it does not
force a second person to make one. Require a review as well if you want two people involved.

The check is advisory until you make it required in the branch rules. Anyone can merge a red
pull request otherwise. You can make it required: the workflow runs on every pull request,
and the `plan` job skips itself when nothing under `infra/` changed. GitHub counts a skipped
job as a pass, so the check never hangs on an unrelated pull request.

### What stays private

The comment holds resource addresses and actions only. The readable plan goes to a file that
nothing uploads, because this repository is public and so are its run logs. Read the
attribute diff by running `terraform plan` locally.

### Identities

The workflow plans as `github-planner`. That account holds `roles/viewer` and
`roles/iam.securityReviewer` on the project, plus `roles/storage.objectViewer` and
`roles/storage.legacyBucketReader` on the state bucket. Every one of those is read-only.
`securityReviewer` is there because the configuration manages IAM members, and a plan reads
each IAM policy to refresh them.

Both accounts are bound by subject, not by repository:

- `github-planner` accepts `repo:tenkenco/declaude:pull_request` only.
- `github-deployer` accepts the main branch and the production environment only.

The binding used to cover the whole repository. Any workflow could then ask for any account,
so a pull request that added one line could have deployed to production. Subjects close that.

The planner cannot write the state lock, so the plan runs with `-lock=false`. A pull request
therefore never blocks a local apply.

Pull requests from forks are skipped. GitHub gives them no OIDC token, so they cannot reach
GCP. A fork that changes `infra/` gets no plan, so read that diff yourself.

### Turning it on

Three steps, in order. Do steps 1 and 2 before you open the pull request. The check already
runs on the pull request that adds it.

1. Apply `cicd.tf` locally once. It creates `github-planner` and its role bindings, and it
   narrows the `github-deployer` binding to subjects.
2. Add a repository secret named `TF_ALERT_EMAIL`, holding the same address as
   `TF_VAR_alert_email`. The plan fails without it, because `alert_email` has no default.
3. Merge the workflow, then make the `plan` check required if you want it to block merges.

Watch the first deploy after step 1. The deployer binding changed, so a failure there shows
as a permission error in the deploy workflow. Roll it back by restoring the previous
`principalSet` member on `deployer_wif`.
