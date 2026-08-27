from __future__ import annotations

from html import escape
import json
import os
from typing import Any
from urllib.parse import quote


SUPPORTED_OWNERS = frozenset(
    {
        "Facilities",
        "AssetLogistics",
        "LanguageAccess",
        "DischargeDME",
        "EVSThroughput",
        "PatientTransport",
    }
)

STATUS_META = {
    "PENDING": {"icon": "schedule", "label": "Queued", "detail": "Waiting for Human Reach delivery", "color": "#5F6368"},
    "DELIVERED": {"icon": "notifications_active", "label": "Delivered", "detail": "Waiting for frontline acknowledgement", "color": "#1A73E8"},
    "ACKNOWLEDGED": {"icon": "how_to_reg", "label": "Acknowledged", "detail": "A frontline responder has accepted the work", "color": "#0F9D58"},
    "BLOCKED": {"icon": "report_problem", "label": "Blocked", "detail": "Human assistance or dependency resolution is required", "color": "#D93025"},
    "COMPLETION_CLAIMED": {"icon": "task_alt", "label": "Completion claimed", "detail": "Trusted evidence and independent verification are still required", "color": "#B06000"},
}


def _text(value: Any, default: str = "—") -> str:
    if not isinstance(value, str):
        value = default
    cleaned = value.strip()
    return escape(cleaned or default)


def _material_icon(name: str, alt_text: str) -> dict[str, Any]:
    return {"materialIcon": {"name": name, "fill": True, "weight": 400}, "altText": alt_text}


def _decorated(*, icon: str, icon_alt: str, top_label: str, text: str, bottom_label: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"startIcon": _material_icon(icon, icon_alt), "topLabel": top_label, "text": text, "wrapText": True}
    if bottom_label:
        payload["bottomLabel"] = bottom_label
    return {"decoratedText": payload}


def _action_button(*, text: str, icon: str, function: str, delivery_id: str, button_type: str, disabled: bool = False, color: dict[str, float] | None = None) -> dict[str, Any]:
    button: dict[str, Any] = {
        "text": text,
        "icon": _material_icon(icon, text),
        "type": button_type,
        "disabled": disabled,
        "onClick": {"action": {"function": function, "parameters": [{"key": "delivery_id", "value": delivery_id}], "loadIndicator": "SPINNER"}},
    }
    if color is not None:
        button["color"] = color
    return button


def _open_console_button(delivery_id: str) -> dict[str, Any] | None:
    base_url = os.environ.get("OPERATIONS_UI_URL", "").strip().rstrip("/")
    if not base_url:
        return None
    url = f"{base_url}/?issue={quote(delivery_id, safe='')}"
    return {
        "text": "Open in Operations Console",
        "icon": _material_icon("open_in_new", "Open Operations Console"),
        "type": "OUTLINED",
        "onClick": {"openLink": {"url": url}},
    }


def _route_display_name(delivery: dict[str, Any]) -> str:
    destination = delivery.get("destination_display_name")
    if isinstance(destination, str) and destination.strip():
        return destination.strip()
    raw = os.environ.get("HUMAN_REACH_ROUTES_JSON", "").strip()
    try:
        routes = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        routes = {}
    owner = delivery.get("owner")
    value = routes.get(owner) if isinstance(routes, dict) else None
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Google Chat"


def _authoritative_status(delivery: dict[str, Any]) -> tuple[str, str, str, str] | None:
    state = str(delivery.get("authoritative_issue_state") or "").strip()
    if state == "VERIFYING":
        return ("fact_check", "Evidence received", "Independent verification is running", "#0F9D58")
    if state == "CLOSED":
        return ("verified", "Verified complete", "Trusted evidence was independently verified and the issue is closed", "#0F9D58")
    if state in {"BLOCKED", "HUMAN_REVIEW", "FAILED"}:
        return ("report_problem", state.replace("_", " ").title(), "Review the current authoritative workflow state in Operations", "#D93025")
    return None


def _status_widget(delivery: dict[str, Any]) -> dict[str, Any]:
    authoritative = _authoritative_status(delivery)
    if authoritative is not None:
        icon, label, detail, color = authoritative
    else:
        status = str(delivery.get("delivery_status", "PENDING"))
        meta = STATUS_META.get(status, {"icon": "info", "label": status.replace("_", " ").title(), "detail": "Review Human Reach delivery state", "color": "#5F6368"})
        icon, label, detail, color = str(meta["icon"]), str(meta["label"]), str(meta["detail"]), str(meta["color"])
    return _decorated(
        icon=icon,
        icon_alt=label,
        top_label="CURRENT STATUS",
        text=f'<font color="{color}"><b>{escape(label)}</b></font> · {escape(detail)}',
        bottom_label="Firestore is authoritative operational truth",
    )


def _last_response_widget(delivery: dict[str, Any]) -> dict[str, Any] | None:
    action = delivery.get("last_response_action")
    if not isinstance(action, str) or not action.strip():
        return None
    actor = _text(delivery.get("last_response_display_name"), "Frontline responder")
    at = _text(delivery.get("last_response_at"), "Recorded by State Authority")
    return _decorated(icon="person_check", icon_alt="Frontline response", top_label="LAST HUMAN RESPONSE", text=f"<b>{escape(action.replace('_', ' ').title())}</b> · {actor}", bottom_label=at)


def _response_buttons(delivery: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(delivery.get("delivery_status", "PENDING"))
    state = str(delivery.get("authoritative_issue_state") or "ACTION_PENDING")
    delivery_id = str(delivery.get("delivery_id", ""))
    if state != "ACTION_PENDING" or status not in {"DELIVERED", "ACKNOWLEDGED"}:
        return []
    return [
        _action_button(text="Acknowledge", icon="how_to_reg", function="humanReach.acknowledge", delivery_id=delivery_id, button_type="FILLED", disabled=(status == "ACKNOWLEDGED"), color={"red": 0.10, "green": 0.70, "blue": 0.66}),
        _action_button(text="Blocked", icon="report_problem", function="humanReach.blocked", delivery_id=delivery_id, button_type="OUTLINED"),
        _action_button(text="Completed", icon="task_alt", function="humanReach.completed", delivery_id=delivery_id, button_type="FILLED_TONAL"),
    ]


def work_card(delivery: dict[str, Any]) -> dict[str, Any]:
    delivery_id = str(delivery.get("delivery_id", ""))
    owner = _text(delivery.get("owner"), "Operations")
    issue_title = _text(delivery.get("issue_title"), "Operational work")
    route = _text(_route_display_name(delivery), "Google Chat")
    state = str(delivery.get("authoritative_issue_state") or "ACTION_PENDING")

    assignment_widgets = [
        _decorated(icon="person", icon_alt="Assigned team or person", top_label="WHO", text=_text(delivery.get("who"), "Frontline team")),
        _decorated(icon="assignment", icon_alt="Operational task", top_label="WHAT", text=_text(delivery.get("what"), "Operational work")),
        _decorated(icon="location_on", icon_alt="Work location", top_label="WHERE", text=_text(delivery.get("where"), "Location pending")),
        _decorated(icon="confirmation_number", icon_alt="Work order", top_label="WORK ORDER", text=_text(delivery.get("work_order"), delivery_id or "Pending"), bottom_label=f"Next Shift issue {escape(delivery_id)}"),
    ]

    human_widgets: list[dict[str, Any]] = [
        _status_widget(delivery),
        _decorated(icon="forum", icon_alt="Google Chat destination", top_label="ROUTED TO", text=route, bottom_label="Resolved deterministically from the specialist owner"),
    ]
    last_response = _last_response_widget(delivery)
    if last_response is not None:
        human_widgets.append(last_response)
    response_buttons = _response_buttons(delivery)
    if response_buttons:
        human_widgets.append({"buttonList": {"buttons": response_buttons}})

    state_detail = {
        "ACTION_PENDING": "Frontline response and trusted evidence are tracked separately",
        "VERIFYING": "Trusted evidence received · independent verification required",
        "CLOSED": "Independent verification accepted trusted evidence",
    }.get(state, "Review current governed state in Operations")

    governance_widgets: list[dict[str, Any]] = [
        _decorated(icon="account_tree", icon_alt="Operational workflow state", top_label="OPERATIONAL WORKFLOW", text=f"<b>{escape(state)}</b> · {escape(state_detail)}", bottom_label="Firestore remains authoritative operational truth"),
        _decorated(icon="verified_user", icon_alt="State Authority protection", top_label="CLOSURE BOUNDARY", text="A human completion claim does <b>not</b> close this issue. Trusted evidence must move it to VERIFYING, then the independent verifier controls CLOSED."),
    ]
    console_button = _open_console_button(delivery_id)
    if console_button is not None:
        governance_widgets.append({"buttonList": {"buttons": [console_button]}})

    return {
        "cardId": f"human-reach-{delivery_id}",
        "card": {
            "header": {"title": issue_title, "subtitle": f"Next Shift Human Reach · {owner}"},
            "sectionDividerStyle": "SOLID_DIVIDER",
            "sections": [
                {"header": "Operational assignment", "widgets": assignment_widgets},
                {"header": "Human Reach", "widgets": human_widgets},
                {"header": "Governed completion", "collapsible": True, "uncollapsibleWidgetsCount": 1, "widgets": governance_widgets},
            ],
        },
    }
