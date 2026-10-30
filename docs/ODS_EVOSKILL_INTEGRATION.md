# ODS and EvoSkill integration

## Integration model

Prey keeps its existing DDGS/GitHub search and Fortytwo model path as the default.
OpenDeepSearch (ODS) is an optional research adapter. It is imported lazily and is
not installed by the base requirements. The web workspace can select ODS only
when the operator explicitly enables it and configures all required providers.

EvoSkill is an offline skill-evolution workflow, not a per-request agent. Run its
optimizer in a separate Python 3.12+ development environment against a reviewed
benchmark. Export only human-reviewed portable Agent Skills into
`agent_skills/<skill-name>/SKILL.md`. Prey loads bounded Markdown instructions;
it does not execute generated Python, shell scripts, Docker tasks or EvoSkill CLI
inside a Gunicorn request.

## ODS environment

Required:
- `ODS_ENABLED=true`
- `ODS_MODEL_NAME=<LiteLLM-supported-model-id>`
- `ODS_SEARCH_PROVIDER=serper` and `SERPER_API_KEY`, OR
  `ODS_SEARCH_PROVIDER=searxng` and `SEARXNG_INSTANCE_URL`
- `ODS_RERANKER=jina` and `JINA_API_KEY` (the current adapter validates Jina only)
- A LiteLLM provider key matching `ODS_MODEL_NAME` (for example,
  `OPENROUTER_API_KEY` for `openrouter/...`, `OPENAI_API_KEY` for `gpt-...`,
  or `ANTHROPIC_API_KEY` for `anthropic/...`)
- Install the optional `opendeepsearch` package and its upstream dependencies in
  a separately validated deployment image; the base Render requirements do not include it.

For SearXNG, `SEARXNG_API_KEY` is optional if the instance does not require it.
ODS model-provider credentials must also be configured according to LiteLLM.
Do not assume the Fortytwo endpoint is compatible until it has been tested
against the exact ODS/LiteLLM version.

ODS dependencies include a substantial browser/ML stack (including Torch,
Transformers, Crawl4AI and SmolAgents). Do not add them to the lightweight
Render requirements until a separate build and memory test succeeds. Prefer a
dedicated ODS worker/service if the deployment resource limits are insufficient.

## Workspace behavior

- The ordinary free-search checkbox remains unchanged and off by default.
- The ODS checkbox appears only when `ODS_ENABLED=true`, the optional package is installed, and search, reranker and LiteLLM credentials are present.
- ODS is never silently used as a fallback: provider/configuration errors are
  surfaced, and the user can choose the existing free search instead.
- One Fortytwo call remains the response-generation path; ODS may make its own
  provider/model calls and those costs are separate.

## EvoSkill workflow

1. Use the official SentientAGI/EvoSkill project in a separate Python 3.12+
   environment and a task-specific benchmark.
2. Run evolution and validation offline. Do not use live user conversations as
   an implicit training dataset.
3. Review diffs and skill contents for correctness, prompt injection, secrets,
   unsafe commands and licensing.
4. Copy approved Markdown skill instructions into `agent_skills/`.
5. Deploy the reviewed skill files with Prey. No optimizer runs in production.

## Validation still required

Before production activation, install ODS in an isolated build and verify its
constructor/API against the pinned upstream revision; test provider failures,
timeouts, output normalization and memory use. Run Prey's unit/integration
tests and a Render staging smoke test. ODS and EvoSkill are not represented as
fully production-validated by this adapter alone.
