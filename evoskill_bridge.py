"""Lightweight bridge for reviewed EvoSkill-generated Agent Skills.

The EvoSkill optimizer itself runs offline in a separate Python 3.12+ workspace.
Prey loads only reviewed, portable Markdown skill instructions at request time;
it never launches arbitrary generated code or runs the EvoSkill loop in web workers.
"""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent / "agent_skills"
MODE_SKILLS = {
    "research": ("research-evidence/SKILL.md",),
    "web3": ("web3-protocol-analysis/SKILL.md",),
    "coding": ("safe-code-review/SKILL.md",),
}


def load_mode_skills(mode: str, max_chars: int = 9000) -> str:
    """Load bounded, repository-managed skill text for a known workspace mode."""
    if mode not in MODE_SKILLS:
        return ""
    sections = []
    remaining = max(0, min(int(max_chars), 12000))
    for relative in MODE_SKILLS[mode]:
        path = (ROOT / relative).resolve()
        if ROOT.resolve() not in path.parents or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            log.warning("Could not read agent skill: %s", relative, exc_info=True)
            continue
        if content and remaining:
            content = content[:remaining]
            sections.append(content)
            remaining -= len(content)
    return "\n\n---\n\n".join(sections)
