from __future__ import annotations

from typing import Any


SUPPORTED_LANGUAGES: set[str] = {
    "Spanish",
    "Thai",
    "Mandarin",
    "Arabic",
}


SYNTHETIC_INTERPRETERS: tuple[dict[str, Any], ...] = (
    {
        "interpreter_id": "INT-ESP-014",
        "name": "Elena Ruiz",
        "languages": {"Spanish"},
        "qualified_medical": True,
        "available": True,
        "next_slot": "19:15",
    },
    {
        "interpreter_id": "INT-THA-008",
        "name": "Narin S.",
        "languages": {"Thai"},
        "qualified_medical": True,
        "available": True,
        "next_slot": "19:05",
    },
    {
        "interpreter_id": "INT-MAN-021",
        "name": "Lin Wei",
        "languages": {"Mandarin"},
        "qualified_medical": True,
        "available": True,
        "next_slot": "19:30",
    },
)


def find_qualified_interpreter(
    language: str,
) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: {language}"
        )

    for interpreter in SYNTHETIC_INTERPRETERS:
        if (
            interpreter["available"]
            and interpreter["qualified_medical"]
            and language in interpreter["languages"]
        ):
            result = dict(interpreter)
            result["languages"] = sorted(
                interpreter["languages"]
            )
            return result

    raise LookupError(
        f"No qualified interpreter available for: {language}"
    )
