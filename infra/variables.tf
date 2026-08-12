variable "project_id" {
  type    = string
  default = "declaude-prod"
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "model_region" {
  description = "Region for the model tier. May differ from the gateway region; the ILB uses global access."
  type        = string
  default     = "us-east1"
}

variable "model_zones" {
  description = "Zones the model MIG may use; spread wide since L4 capacity varies by zone."
  type        = list(string)
  default     = ["us-east1-b", "us-east1-c", "us-east1-d"] # us-central1 a/b/c were stocked out 2026-08-12; us-east1-b probed OK
}

variable "model_machine_type" {
  description = "GPU machine type for vLLM. g2-standard-8 = 1x L4 (24GB). Bump to g2-standard-24 (2x L4) after quota increase."
  type        = string
  default     = "g2-standard-8"
}

variable "model_accelerator" {
  type    = object({ type = string, count = number })
  default = { type = "nvidia-l4", count = 1 }
}

variable "model_hf_id" {
  description = "HuggingFace model served by vLLM."
  type        = string
  default     = "Qwen/Qwen2.5-14B-Instruct-AWQ" # 32B-AWQ does not fit 8k ctx KV on 1xL4; upgrade to 32B with 2xL4 (g2-standard-24)
}

variable "model_served_name" {
  type    = string
  default = "qwen2.5-14b-instruct"
}

variable "vllm_max_model_len" {
  description = "Context window. Bounded to fit 32B-AWQ KV cache on a single L4."
  type        = number
  default     = 16384
}

variable "model_replicas" {
  type    = number
  default = 1
}

variable "clerk_jwks_url" {
  type    = string
  default = "https://humble-arachnid-95.clerk.accounts.dev/.well-known/jwks.json"
}

variable "free_tier_monthly_limit" {
  type    = number
  default = 100
}

variable "github_repo" {
  description = "owner/name allowed to deploy via Workload Identity Federation."
  type        = string
  default     = "tenkenco/declaude"
}
