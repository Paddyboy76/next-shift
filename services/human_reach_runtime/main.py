from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

from flask import Flask
from flask import jsonify
from flask import request
import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import id_token
import requests


CHAT_API = "https://chat.googleapis.com/v1"
CHAT_SCOPE = "https://www.googleapis.com/auth/chat.bot"
TIMEOUT_SECONDS = 20
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
ALLOWED_FUNCTIONS = {
    "humanReach.acknowledge": "acknowledge",
    "humanReach.blocked": "blocked",
    "humanReach.completed": "completed",
}

app = Flask(__name__)


def _state_url() -> str:
    value = os.environ.get(
        "STATE_AUTHORITY_URL",
        "",
    ).strip()

    if not value:
        raise RuntimeError("STATE_AUTHORITY_URL is required")

    return value.rstrip("/")


def _routes() -> dict[str, str]:
    raw = os.environ.get(
        "HUMAN_REACH_ROUTES_JSON",
        "",
    ).strip()

    if not raw:
        raise RuntimeError("HUMAN_REACH_ROUTES_JSON is required")

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "HUMAN_REACH_ROUTES_JSON must be valid JSON"
        ) from exc

    if not isinstance(parsed, dict):
        raise RuntimeError(
            "HUMAN_REACH_ROUTES_JSON must be an object"
        )

    routes: dict[str, str] = {}

    for owner in SUPPORTED_OWNERS:
        value = parsed.get(owner)

        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"Missing Human Reach route for {owner}"
            )

        routes[owner] = value.strip()

    if set(parsed) != SUPPORTED_OWNERS:
        raise RuntimeError(
            "Human Reach routes must contain only canonical owners"
        )

    return routes


def _state_headers() -> dict[str, str]:
    state_url = _state_url()
    token = id_token.fetch_id_token(
        GoogleAuthRequest(),
        state_url,
    )

    if not token:
        raise RuntimeError(
            "Unable to obtain State Authority identity token"
        )

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _chat_token() -> str:
    credentials, _ = google.auth.default(
        scopes=[CHAT_SCOPE]
    )
    credentials.refresh(GoogleAuthRequest())

    if not credentials.token:
        raise RuntimeError(
            "Unable to obtain Google Chat app token"
        )

    return credentials.token


def _chat_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_chat_token()}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def _json_response(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid JSON response: status={response.status_code} "
            f"body={response.text[:1000]}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Expected JSON object response")

    if response.status_code >= 400:
        raise RuntimeError(
            f"Remote request failed: status={response.status_code} "
            f"body={json.dumps(payload)[:1000]}"
        )

    return payload


def _get_delivery(delivery_id: str) -> dict[str, Any]:
    response = requests.get(
        (
            f"{_state_url()}/v1/human-reach/deliveries/"
            f"{delivery_id}"
        ),
        headers=_state_headers(),
        timeout=TIMEOUT_SECONDS,
    )
    payload = _json_response(response)
    delivery = payload.get("delivery")

    if not isinstance(delivery, dict):
        raise RuntimeError("State Authority returned invalid delivery")

    return delivery


def _mark_delivered(
    *,
    delivery_id: str,
    space_name: str,
    display_name: str,
    message_name: str,
) -> dict[str, Any]:
    response = requests.post(
        (
            f"{_state_url()}/v1/human-reach/deliveries/"
            f"{delivery_id}/delivered"
        ),
        headers=_state_headers(),
        json={
            "destination_space": space_name,
            "destination_display_name": display_name,
            "message_name": message_name,
        },
        timeout=TIMEOUT_SECONDS,
    )
    return _json_response(response)


def _record_response(
    *,
    delivery_id: str,
    action: str,
    actor_user: str,
    actor_display_name: str,
    source_space: str,
    source_message: str,
) -> dict[str, Any]:
    response = requests.post(
        (
            f"{_state_url()}/v1/human-reach/deliveries/"
            f"{delivery_id}/respond"
        ),
        headers=_state_headers(),
        json={
            "action": action,
            "actor_user": actor_user,
            "actor_display_name": actor_display_name,
            "source_space": source_space,
            "source_message": source_message,
        },
        timeout=TIMEOUT_SECONDS,
    )
    return _json_response(response)


def _list_named_spaces() -> list[dict[str, Any]]:
    spaces: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        params: dict[str, Any] = {
            "pageSize": 100,
            "filter": 'space_type = "SPACE"',
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            f"{CHAT_API}/spaces",
            headers=_chat_headers(),
            params=params,
            timeout=TIMEOUT_SECONDS,
        )
        payload = _json_response(response)

        page = payload.get("spaces", [])

        if not isinstance(page, list):
            raise RuntimeError("Google Chat returned invalid spaces list")

        spaces.extend(
            item
            for item in page
            if isinstance(item, dict)
        )

        token = payload.get("nextPageToken")

        if not isinstance(token, str) or not token:
            break

        page_token = token

    return spaces


def _resolve_space(owner: str) -> tuple[str, str]:
    display_name = _routes()[owner]
    matches = [
        space
        for space in _list_named_spaces()
        if space.get("displayName") == display_name
    ]

    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one Google Chat space named "
            f"{display_name!r}; found {len(matches)}"
        )

    space_name = matches[0].get("name")

    if not isinstance(space_name, str) or not space_name.startswith(
        "spaces/"
    ):
        raise RuntimeError("Resolved Chat space has invalid resource name")

    return space_name, display_name


def _message_id(delivery_id: str) -> str:
    digest = hashlib.sha256(
        delivery_id.encode("utf-8")
    ).hexdigest()[:40]
    return f"client-next-shift-{digest}"


def _request_id(delivery_id: str) -> str:
    digest = hashlib.sha256(
        f"human-reach:{delivery_id}".encode("utf-8")
    ).hexdigest()
    return (
        f"{digest[:8]}-{digest[8:12]}-{digest[12:16]}-"
        f"{digest[16:20]}-{digest[20:32]}"
    )


def _button(
    *,
    label: str,
    function: str,
    delivery_id: str,
    disabled: bool = False,
) -> dict[str, Any]:
    return {
        "text": label,
        "disabled": disabled,
        "onClick": {
            "action": {
                "function": function,
                "parameters": [
                    {
                        "key": "delivery_id",
                        "value": delivery_id,
                    }
                ],
                "loadIndicator": "SPINNER",
            }
        },
    }


def _status_text(delivery: dict[str, Any]) -> str:
    status = str(delivery.get("delivery_status", "PENDING"))

    return {
        "PENDING": "Queued for frontline delivery",
        "DELIVERED": "Delivered - waiting for acknowledgement",
        "ACKNOWLEDGED": "Acknowledged by frontline worker",
        "BLOCKED": "Frontline worker reported blocked - issue remains open",
        "COMPLETION_CLAIMED": (
            "Completion claimed - trusted evidence and independent "
            "verification are still required"
        ),
    }.get(status, status)


def _work_card(delivery: dict[str, Any]) -> dict[str, Any]:
    delivery_id = str(delivery.get("delivery_id", ""))
    status = str(delivery.get("delivery_status", "PENDING"))

    widgets: list[dict[str, Any]] = [
        {
            "decoratedText": {
                "topLabel": "WHO",
                "text": str(delivery.get("who", "Unknown")),
            }
        },
        {
            "decoratedText": {
                "topLabel": "WHAT",
                "text": str(delivery.get("what", "Operational work")),
                "wrapText": True,
            }
        },
        {
            "decoratedText": {
                "topLabel": "WHERE",
                "text": str(delivery.get("where", "Unknown")),
                "wrapText": True,
            }
        },
        {
            "decoratedText": {
                "topLabel": "WORK ORDER",
                "text": str(delivery.get("work_order", delivery_id)),
            }
        },
        {
            "decoratedText": {
                "topLabel": "HUMAN REACH STATUS",
                "text": _status_text(delivery),
                "wrapText": True,
            }
        },
    ]

    if status in {"DELIVERED", "ACKNOWLEDGED"}:
        widgets.append(
            {
                "buttonList": {
                    "buttons": [
                        _button(
                            label="Acknowledge",
                            function="humanReach.acknowledge",
                            delivery_id=delivery_id,
                            disabled=(status == "ACKNOWLEDGED"),
                        ),
                        _button(
                            label="Blocked",
                            function="humanReach.blocked",
                            delivery_id=delivery_id,
                        ),
                        _button(
                            label="Completed",
                            function="humanReach.completed",
                            delivery_id=delivery_id,
                        ),
                    ]
                }
            }
        )

    return {
        "cardId": f"human-reach-{delivery_id}",
        "card": {
            "header": {
                "title": "Next Shift frontline work",
                "subtitle": str(delivery.get("owner", "Operations")),
            },
            "sections": [
                {
                    "header": str(
                        delivery.get("issue_title", "Operational work")
                    ),
                    "widgets": widgets,
                }
            ],
        },
    }


def _message_body(delivery: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": (
            f"Next Shift work: {delivery.get('issue_title', 'Operational work')}"
        ),
        "cardsV2": [_work_card(delivery)],
    }


def _send_delivery(delivery: dict[str, Any]) -> dict[str, Any]:
    owner = delivery.get("routing_key")

    if owner not in SUPPORTED_OWNERS:
        raise RuntimeError("Delivery has unsupported routing key")

    space_name, display_name = _resolve_space(str(owner))
    delivery_for_card = {
        **delivery,
        "delivery_status": "DELIVERED",
    }

    response = requests.post(
        f"{CHAT_API}/{space_name}/messages",
        headers=_chat_headers(),
        params={
            "messageId": _message_id(str(delivery["delivery_id"])),
            "requestId": _request_id(str(delivery["delivery_id"])),
        },
        json=_message_body(delivery_for_card),
        timeout=TIMEOUT_SECONDS,
    )

    if response.status_code == 409:
        # Idempotent retry: the custom message ID already exists. Resolve it
        # deterministically instead of creating another Chat message.
        message_name = (
            f"{space_name}/messages/"
            f"{_message_id(str(delivery['delivery_id']))}"
        )
    else:
        payload = _json_response(response)
        message_name = payload.get("name")

        if not isinstance(message_name, str) or not message_name:
            raise RuntimeError("Google Chat did not return a message name")

    return _mark_delivered(
        delivery_id=str(delivery["delivery_id"]),
        space_name=space_name,
        display_name=display_name,
        message_name=message_name,
    )


def _decode_pubsub_event(payload: dict[str, Any]) -> dict[str, Any]:
    message = payload.get("message")

    if not isinstance(message, dict):
        raise ValueError("Missing Pub/Sub message")

    data = message.get("data")

    if not isinstance(data, str) or not data:
        raise ValueError("Missing Pub/Sub data")

    decoded = json.loads(
        base64.b64decode(data).decode("utf-8")
    )

    if not isinstance(decoded, dict):
        raise ValueError("Invalid Human Reach event")

    if decoded.get("event_type") != "human_reach.delivery.requested":
        raise ValueError("Unsupported Human Reach event type")

    if decoded.get("schema_version") != "human-reach.delivery.v1":
        raise ValueError("Unsupported Human Reach schema version")

    delivery_id = decoded.get("delivery_id")

    if not isinstance(delivery_id, str) or not delivery_id:
        raise ValueError("Missing delivery ID")

    return decoded


def _event_type(event: dict[str, Any]) -> str:
    value = event.get("type")

    if isinstance(value, str) and value:
        return value

    value = event.get("eventType")
    return value if isinstance(value, str) else ""


def _delivery_id_from_chat_event(event: dict[str, Any]) -> str:
    common = event.get("common")

    if not isinstance(common, dict):
        raise ValueError("Missing Chat common event object")

    parameters = common.get("parameters")

    if not isinstance(parameters, dict):
        raise ValueError("Missing Chat action parameters")

    delivery_id = parameters.get("delivery_id")

    if not isinstance(delivery_id, str) or not delivery_id:
        raise ValueError("Missing Chat delivery ID")

    return delivery_id


def _handle_card_click(event: dict[str, Any]) -> dict[str, Any]:
    common = event.get("common")

    if not isinstance(common, dict):
        raise ValueError("Missing Chat common event object")

    function = common.get("invokedFunction")
    action = ALLOWED_FUNCTIONS.get(function)

    if action is None:
        raise ValueError("Unsupported Chat card action")

    delivery_id = _delivery_id_from_chat_event(event)
    user = event.get("user")
    space = event.get("space")
    message = event.get("message")

    if not isinstance(user, dict):
        raise ValueError("Missing Chat user")

    if not isinstance(space, dict):
        raise ValueError("Missing Chat space")

    if not isinstance(message, dict):
        raise ValueError("Missing Chat message")

    actor_user = user.get("name")
    actor_display_name = user.get("displayName") or actor_user
    source_space = space.get("name")
    source_message = message.get("name")

    if not all(
        isinstance(value, str) and value
        for value in (
            actor_user,
            actor_display_name,
            source_space,
            source_message,
        )
    ):
        raise ValueError("Incomplete Chat interaction identity")

    payload = _record_response(
        delivery_id=delivery_id,
        action=action,
        actor_user=str(actor_user),
        actor_display_name=str(actor_display_name),
        source_space=str(source_space),
        source_message=str(source_message),
    )
    delivery = payload.get("delivery")

    if not isinstance(delivery, dict):
        raise RuntimeError("State Authority returned invalid delivery")

    return {
        "actionResponse": {
            "type": "UPDATE_MESSAGE",
        },
        "text": (
            f"Next Shift work: {delivery.get('issue_title', 'Operational work')}"
        ),
        "cardsV2": [_work_card(delivery)],
    }


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "next-shift-human-reach",
            "channel": "google_chat",
        }
    )


@app.post("/pubsub")
def pubsub_push():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({"error": "invalid_request"}), 400

    try:
        event = _decode_pubsub_event(payload)
        delivery = _get_delivery(str(event["delivery_id"]))

        if delivery.get("delivery_status") != "PENDING":
            return "", 204

        _send_delivery(delivery)
    except ValueError as exc:
        return jsonify({"error": "invalid_event", "detail": str(exc)}), 400
    except Exception as exc:
        return (
            jsonify(
                {
                    "error": "human_reach_delivery_failed",
                    "detail": type(exc).__name__,
                }
            ),
            500,
        )

    return "", 204


@app.post("/chat")
def chat_event():
    event = request.get_json(silent=True)

    if not isinstance(event, dict):
        return jsonify({"text": "Invalid Next Shift interaction."}), 400

    event_type = _event_type(event)

    if event_type == "CARD_CLICKED":
        try:
            return jsonify(_handle_card_click(event))
        except Exception:
            return jsonify(
                {
                    "text": (
                        "Next Shift could not record that response. "
                        "The operational issue was not changed."
                    )
                }
            )

    if event_type == "ADDED_TO_SPACE":
        return jsonify(
            {
                "text": (
                    "Next Shift Human Reach is connected. "
                    "Operational work cards will appear here when routed "
                    "to this space."
                )
            }
        )

    if event_type == "MESSAGE":
        return jsonify(
            {
                "text": (
                    "Next Shift Human Reach is delivery-driven. "
                    "Use the buttons on an operational work card to respond."
                )
            }
        )

    return "", 204
