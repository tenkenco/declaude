# Show HN

**Title** (80 char limit — this is 74):
Show HN: Declaude – strip Claude's sycophantic voice without spending tokens

**URL**: https://speak-english.tenken.co

**First comment** (post immediately after submitting):

I got tired of reading "Great question! You're absolutely right! This robust,
comprehensive solution..." before every actual answer, so I built a service that rewrites
it into plain English.

The part I think is interesting: it runs as a Claude Code MessageDisplay hook, which fires
*after* Claude finishes generating. The rewrite happens on my GPU, never touches Anthropic's
API, and only changes what renders. Your transcript and token bill are untouched — the
de-Claudification is free in tokens.

Stack: Qwen2.5-14B-AWQ on vLLM on a spot L4, FastAPI gateway on Cloud Run, Clerk for auth
with OAuth 2.1 + PKCE for MCP clients (so `claude mcp add` works with zero flags — browser
sign-in, no key pasting). 100 translations and 5 documents free per month.

Two things I learned building it that might be useful to others:

1. Dogfooding a 48-paragraph document returned 47. I was batching paragraphs into one model
   call and re-splitting on paragraph count; whenever the model merged two, the fallback
   blanked the rest. Silent data loss that scaled with document size. One call per block,
   gathered concurrently, made it both correct and 5x faster — vLLM batches concurrent
   requests better than my sequential loop did.

2. Non-English input came back in the wrong language (Japanese in, Chinese out). Pinning
   the language in the system prompt helped but did not hold. What actually fixed it was
   checking the output at the boundary: compare the dominant Unicode script of the rewrite
   against the input, and return the original when they differ. Prompts are a request;
   validation is a guarantee.

It grew out of gvzdv's open-source claudish-to-english (a local Ollama hook) — this is the
hosted version. Source is MIT: https://github.com/tenkenco/declaude
