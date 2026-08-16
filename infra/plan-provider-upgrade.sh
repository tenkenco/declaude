#!/usr/bin/env bash
# Test a provider upgrade without touching prod state.
#
# There is no staging environment — one project, one state prefix, no workspaces — and standing
# one up would create a real L4 GPU MIG and load balancers. This is the cheap equivalent: copy
# prod state to a scratch prefix, run the plan against that copy, and report the diff. Plan is
# read-only against GCP, and pointing it at a copied state means prod state cannot be rewritten
# even by a state schema upgrade.
#
# Usage:  gcloud auth login && gcloud auth application-default login
#         ./plan-provider-upgrade.sh [git-ref]     # default: origin/pr65
set -euo pipefail

REF="${1:?usage: plan-provider-upgrade.sh <git-ref>}"
BUCKET="declaude-prod-tfstate"
SCRATCH="upgrade-test-$(date +%Y%m%d-%H%M%S)"
INFRA="$(cd "$(dirname "$0")" && pwd)"

echo "==> copying prod state to scratch prefix: $SCRATCH"
gcloud storage cp "gs://$BUCKET/prod/default.tfstate" "gs://$BUCKET/$SCRATCH/default.tfstate"

cleanup() {
  echo "==> removing scratch state"
  gcloud storage rm -r "gs://$BUCKET/$SCRATCH" 2>/dev/null || true
}
trap cleanup EXIT

cd "$INFRA"
ORIG_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git stash -u -q 2>/dev/null || true
git checkout -q "$REF"

rm -rf .terraform

echo "==> init against scratch state with the upgraded provider"
terraform init -upgrade -input=false -reconfigure \
  -backend-config="bucket=$BUCKET" -backend-config="prefix=$SCRATCH"

echo "==> provider versions now in use"
terraform version

echo "==> plan (read-only; nothing is applied)"
set +e
terraform plan -input=false -lock=false -detailed-exitcode -out=/tmp/upgrade.tfplan
CODE=$?
set -e

case $CODE in
  0) echo "RESULT: clean — plan converges to zero diff on the new provider. Safe to merge." ;;
  2) echo "RESULT: the plan is NOT empty. Inspect it before merging:"
     terraform show -no-color /tmp/upgrade.tfplan | head -120 ;;
  *) echo "RESULT: plan errored (exit $CODE) — the upgrade needs config changes." ;;
esac

git checkout -q "$ORIG_BRANCH"
git stash pop -q 2>/dev/null || true
exit $CODE
