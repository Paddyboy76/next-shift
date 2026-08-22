from __future__ import annotations

from typing import Any

import requests

import main as human_reach_runtime


def _configured_display_names() -> set[str]:
    return set(human_reach_runtime._routes().values())


def _display_name_for_space(
    *,
    space_name: str,
    inline_display_name: Any,
) -> str | None:
    configured = _configured_display_names()

    if isinstance(inline_display_name, str):
        cleaned = inline_display_name.strip()
        if cleaned in configured:
            return cleaned

    response = requests.get(
        f"{human_reach_runtime.CHAT_API}/{space_name}",
        headers=human_reach_runtime._chat_headers(),
        timeout=human_reach_runtime.TIMEOUT_SECONDS,
    )
    payload = human_reach_runtime._json_response(response)

    returned_name = payload.get("name")
    display_name = payload.get("displayName")

    if returned_name != space_name:
        raise RuntimeError(
            "Google Chat returned metadata for an unexpected space"
        )

    if not isinstance(display_name, str) or not display_name.strip():
        human_reach_runtime.app.logger.warning(
            "Ignoring Google Chat route without a usable display name: %s",
            space_name,
        )
        return None

    cleaned = display_name.strip()

    if cleaned not in configured:
        human_reach_runtime.app.logger.warning(
            "Ignoring Google Chat route outside configured allowlist: "
            "space=%s display_name=%r",
            space_name,
            cleaned,
        )
        return None

    return cleaned


def _event_space(event: dict[str, Any]) -> tuple[str, str] | None:
    space = event.get("space")

    if not isinstance(space, dict):
        return None

    space_name = space.get("name")

    if (
        not isinstance(space_name, str)
        or not space_name.startswith("spaces/")
    ):
        return None

    display_name = _display_name_for_space(
        space_name=space_name,
        inline_display_name=space.get("displayName"),
    )

    if display_name is None:
        return None

    return space_name, display_name


def register_space_from_event(
    event: dict[str, Any],
) -> dict[str, Any] | None:
    resolved = _event_space(event)

    if resolved is None:
        return None

    space_name, display_name = resolved
    response = requests.post(
        (
            f"{human_reach_runtime._state_url()}"
            "/v1/human-reach/routes/register"
        ),
        headers=human_reach_runtime._state_headers(),
        json={
            "space_name": space_name,
            "display_name": display_name,
        },
        timeout=human_reach_runtime.TIMEOUT_SECONDS,
    )
    payload = human_reach_runtime._json_response(response)
    route = payload.get("route")

    if not isinstance(route, dict):
        raise RuntimeError("State Authority returned invalid Chat route")

    return route


def deactivate_space_from_event(
    event: dict[str, Any],
) -> dict[str, Any] | None:
    resolved = _event_space(event)

    if resolved is None:
        return None

    space_name, display_name = resolved
    response = requests.post(
        (
            f"{human_reach_runtime._state_url()}"
            "/v1/human-reach/routes/deactivate"
        ),
        headers=human_reach_runtime._state_headers(),
        json={
            "space_name": space_name,
            "display_name": display_name,
        },
        timeout=human_reach_runtime.TIMEOUT_SECONDS,
    )
    payload = human_reach_runtime._json_response(response)
    route = payload.get("route")

    if not isinstance(route, dict):
        raise RuntimeError("State Authority returned invalid Chat route")

    return route


def resolve_space(owner: str) -> tuple[str, str]:
    routes = human_reach_runtime._routes()

    if owner not in routes:
        raise RuntimeError("Unsupported Human Reach route owner")

    display_name = routes[owner]
    response = requests.get(
        (
            f"{human_reach_runtime._state_url()}"
            "/v1/human-reach/routes/resolve"
        ),
        headers=human_reach_runtime._state_headers(),
        params={"display_name": display_name},
        timeout=human_reach_runtime.TIMEOUT_SECONDS,
    )
    payload = human_reach_runtime._json_response(response)
    route = payload.get("route")

    if not isinstance(route, dict):
        raise RuntimeError("State Authority returned invalid Chat route")

    space_name = route.get("space_name")
    returned_display_name = route.get("display_name")

    if (
        not isinstance(space_name, str)
        or not space_name.startswith("spaces/")
        or returned_display_name != display_name
        or route.get("active") is not True
    ):
        raise RuntimeError("State Authority returned unusable Chat route")

    return space_name, display_name
