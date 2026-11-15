from dataclasses import dataclass, field
from typing import Any

VALID_STATES = {"queued", "claimed", "running", "succeeded", "failed", "cancelled"}

TRANSITIONS = {
    "queued": {"claimed", "cancelled"},
    "claimed": {"running", "failed", "cancelled"},
    "running": {"succeeded", "failed", "cancelled"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
}

@dataclass
class Job:
    id: str
    incident_id: str
    job_type: str
    state: str = "queued"
    idempotency_key: str = ""
    source_acquisitions: list[str] = field(default_factory=list)
    parameters: dict[str, Any] = field(default_factory=dict)
    processor_version: str = ""
    retry_count: int = 0
    error_message: str = ""

    def transition(self, new_state: str) -> None:
        if new_state not in VALID_STATES:
            raise ValueError(f"unknown state {new_state}")
        if new_state == self.state:
            raise ValueError("no-op transition not allowed")
        if new_state not in TRANSITIONS[self.state]:
            raise ValueError(f"illegal transition {self.state} -> {new_state}")
        self.state = new_state

    def validate(self) -> None:
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if not self.idempotency_key:
            raise ValueError("idempotency_key required")
        if not self.job_type:
            raise ValueError("job_type required")
