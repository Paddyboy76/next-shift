from __future__ import annotations

from typing import Literal


WorkflowState = Literal[
    "RECEIVED",
    "TRIAGED",
    "ASSIGNED",
    "ACTION_PENDING",
    "VERIFYING",
    "CLOSED",
    "BLOCKED",
    "HUMAN_REVIEW",
    "FAILED",
]


VALID_STATES: set[str] = {
    "RECEIVED",
    "TRIAGED",
    "ASSIGNED",
    "ACTION_PENDING",
    "VERIFYING",
    "CLOSED",
    "BLOCKED",
    "HUMAN_REVIEW",
    "FAILED",
}


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "RECEIVED": {"TRIAGED", "HUMAN_REVIEW", "FAILED"},
    "TRIAGED": {"ASSIGNED", "HUMAN_REVIEW", "FAILED"},
    "ASSIGNED": {
        "ACTION_PENDING",
        "BLOCKED",
        "HUMAN_REVIEW",
        "FAILED",
    },
    "ACTION_PENDING": {
        "VERIFYING",
        "BLOCKED",
        "HUMAN_REVIEW",
        "FAILED",
    },
    "VERIFYING": {
        "CLOSED",
        "ACTION_PENDING",
        "BLOCKED",
        "HUMAN_REVIEW",
        "FAILED",
    },
    "BLOCKED": {
        "ASSIGNED",
        "ACTION_PENDING",
        "HUMAN_REVIEW",
        "FAILED",
    },
    "HUMAN_REVIEW": {
        "ASSIGNED",
        "ACTION_PENDING",
        "FAILED",
    },
    "FAILED": set(),
    "CLOSED": set(),
}
