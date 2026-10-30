# Prey EvoSkill benchmark starter set

These small CSV files are smoke-test seeds, not a statistically meaningful
benchmark. Expand each mode with reviewed examples and objective ground truth
before running EvoSkill optimization.

## Intended workflow

1. Use an isolated Python 3.12+ development environment.
2. Install the official [Sentient EvoSkill](https://github.com/sentient-agi/EvoSkill)
   project there; do not add its optimizer, Docker runner, or agent CLIs to the
   lightweight Render web process.
3. Create one EvoSkill project per mode (research, Web3, coding), configure the
   matching CSV question/ground_truth columns, and use a supported harness.
4. Run baseline evaluation first, then a bounded evolution run (start with 3-5
   iterations and low concurrency).
5. Evaluate the best candidate on a held-out set. Review every generated skill
   and prompt for factual quality, prompt injection, secrets, unsafe commands,
   and regressions.
6. Export only human-approved portable Agent Skills into
   `agent_skills/<skill-name>/SKILL.md`. Production Prey continues to load only
   reviewed Markdown; it never executes generated scripts.

## Cost and safety

EvoSkill performs repeated agent and evaluator calls; it is not a free,
per-request feature. Do not connect it to Fortytwo or spend production API
credits until provider compatibility and a separate budget have been tested.
Never use real user conversations as an implicit training dataset.

## ROMA adapter

`sentient_stack/roma_adapter.py` is a separate, opt-in integration point for
the official `roma-dspy` package. It is disabled unless
`PREY_ROMA_ENABLED=true`, the package is installed, and a supported provider
key is configured. It uses ROMA's public `solve(task, max_depth=...)` API with
a maximum depth of two. It is not yet connected to the existing Flask workspace;
that preserves the current Fortytwo path and UI while the adapter is validated
in isolation.

ROMA requires Python 3.12+ and a supported LLM provider. Its calls are separate
from Fortytwo and may incur additional charges. The Fortytwo API key alone is
not treated as a compatible provider credential.
