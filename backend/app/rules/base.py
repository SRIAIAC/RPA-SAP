"""RuleResult: the uniform output shape every rule module returns.

The Business Rules Engine is deterministic by design — every function here
is a pure function of its inputs (no randomness, no I/O). AI (app/ai/) may
feed a rule function a classification/recommendation as an *input*, but the
rule function's `decision` is always what the workflow engine actually acts
on. AI never overrides a rule result.

Every rule cites the specific knowledge_base/*.md rule number its threshold
comes from, so the numbers in this module are traceable to the hand-authored
SOP documents rather than being invented.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleResult:
    decision: str
    reasons: list[str] = field(default_factory=list)
    recommended_action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
