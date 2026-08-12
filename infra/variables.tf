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

variable "model_machine_type" {
  description = "GPU machine type for vLLM. g2-standard-8 = 1x L4 (24GB). Bump to g2-standard-24 (2x L4) after quota increase."
  type        = string
  default     = "g2-standard-8"
}

variable "model_accelerator" {
  type = object({ type = string, count = number })
  default = { type = "nvidia-l4", count = 1 }
}

variable "model_hf_id" {
  description = "HuggingFace model served by vLLM."
  type        = string
  default     = "Qwen/Qwen2.5-32B-Instruct-AWQ"
}

variable "model_served_name" {
  type    = string
  default = "qwen2.5-32b-instruct"
}

variable "vllm_max_model_len" {
  description = "Context window. Bounded to fit 32B-AWQ KV cache on a single L4."
  type        = number
  default     = 8192
}

variable "model_replicas" {
  type    = number
  default = 1
}

variable "clerk_jwks_url" {
  type    = string
  default = "https://sincere-redfish-88.clerk.accounts.dev/.well-known/jwks.json"
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
