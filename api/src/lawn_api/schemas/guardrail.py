from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Severity is deliberately small and ordered by how much it should interrupt.
#   ok              - checked, nothing to say (usually filtered out of the UI)
#   caution         - advisory; the operator may have a reason, never blocks a save
#   cannot_evaluate - a required input was missing, so the check could not run
#
# There is no "blocked" level in Phase 2c: every guardrail here is advisory. A
# check that cannot run reports cannot_evaluate rather than passing silently --
# a guardrail that fails silent is worse than none, because it reads as all-clear.
GuardrailSeverity = Literal["ok", "caution", "cannot_evaluate"]


class GuardrailFinding(BaseModel):
    """One structured result from evaluating a guardrail.

    The shape is intended to serve three consumers without change: the API
    response at log time, the dashboard's outstanding-cautions widget, and
    (Phase 3) the AI layer, which can reason over the numbers rather than
    re-deriving them.
    """

    model_config = ConfigDict(from_attributes=True)

    code: str  # stable identifier, e.g. "nitrogen_load_30d"
    severity: GuardrailSeverity
    title: str
    message: str
    # The values behind the message, so a consumer can render or reason without
    # parsing prose. e.g. {"applied": 1.2, "threshold": 1.0, "window_days": 30}.
    numbers: dict[str, float] = Field(default_factory=dict)
    # Set when a finding is about one product (missing analysis, over its cap).
    product_id: UUID | None = None
    product_name: str | None = None

    @property
    def evaluatable(self) -> bool:
        return self.severity != "cannot_evaluate"
