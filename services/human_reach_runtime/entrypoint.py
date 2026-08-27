from flask import jsonify
from flask import request

from auth import authorize_chat_request
from auth import authorize_operations_request
from auth import authorize_pubsub_request
import durable_routes
import main as human_reach_runtime
import photo_proof
from main import _routes
from main import app
from rich_card import work_card as base_work_card


# Keep the proven delivery/action engine in main.py and replace only the
# integration adapters at process startup. Delivery continues to use the same
# Human Reach engine, while durable route resolution is owned by State
# Authority instead of Google Chat space-list discovery.
def work_card(delivery):
    return photo_proof.decorate_card(
        delivery,
        base_work_card(delivery),
    )


human_reach_runtime._work_card = work_card
human_reach_runtime._resolve_space = durable_routes.resolve_space
_original_chat_event = human_reach_runtime.chat_event


def send_delivery_in_issue_thread(delivery):
    owner = delivery.get("routing_key")
    if owner not in human_reach_runtime.SUPPORTED_OWNERS:
        raise RuntimeError("Delivery has unsupported routing key")

    space_name, display_name = human_reach_runtime._resolve_space(str(owner))
    delivery_id = str(delivery["delivery_id"])
    delivery_for_card = {
        **delivery,
        "delivery_status": "DELIVERED",
    }
    body = {
        **human_reach_runtime._message_body(delivery_for_card),
        "thread": {
            "threadKey": photo_proof.thread_key(delivery_id),
        },
    }
    response = human_reach_runtime.requests.post(
        f"{human_reach_runtime.CHAT_API}/{space_name}/messages",
        headers=human_reach_runtime._chat_headers(),
        params={
            "messageId": human_reach_runtime._message_id(delivery_id),
            "requestId": human_reach_runtime._request_id(delivery_id),
            "messageReplyOption": "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD",
        },
        json=body,
        timeout=human_reach_runtime.TIMEOUT_SECONDS,
    )

    if response.status_code == 409:
        message_name = (
            f"{space_name}/messages/"
            f"{human_reach_runtime._message_id(delivery_id)}"
        )
    else:
        payload = human_reach_runtime._json_response(response)
        message_name = payload.get("name")
        if not isinstance(message_name, str) or not message_name:
            raise RuntimeError("Google Chat did not return a message name")

    return human_reach_runtime._mark_delivered(
        delivery_id=delivery_id,
        space_name=space_name,
        display_name=display_name,
        message_name=message_name,
    )


human_reach_runtime._send_delivery = send_delivery_in_issue_thread


@app.before_request
def verify_ingress_identity():
    authorization = request.headers.get(
        "Authorization"
    )

    if (
        request.method == "POST"
        and request.path in {"/", "/chat"}
    ):
        if not authorize_chat_request(
            authorization
        ):
            return (
                jsonify(
                    {"error": "chat_authentication_required"}
                ),
                401,
            )

    if (
        request.method == "POST"
        and request.path == "/pubsub"
    ):
        if not authorize_pubsub_request(
            authorization
        ):
            return (
                jsonify(
                    {"error": "pubsub_authentication_required"}
                ),
                401,
            )

    if (
        request.method == "POST"
        and request.path.startswith("/v1/human-reach/deliveries/")
        and request.path.endswith("/refresh")
    ):
        if not authorize_operations_request(
            authorization
        ):
            return (
                jsonify(
                    {"error": "operations_authentication_required"}
                ),
                401,
            )

    return None


def _handle_photo_message(event):
    if not photo_proof.has_image_attachments(event):
        return None

    delivery_id = photo_proof.delivery_id_from_event(event)
    if delivery_id is None:
        return jsonify(
            {
                "text": (
                    "Photo proof was not attached to a Next Shift work thread. "
                    "Open the Facilities work card, choose Completed, then reply "
                    "in that same thread with BEFORE and AFTER images and @mention Next Shift."
                )
            }
        )

    try:
        delivery = human_reach_runtime._get_delivery(delivery_id)
        result = photo_proof.process_message(
            event=event,
            delivery=delivery,
            chat_token=human_reach_runtime._chat_token(),
        )
    except ValueError as exc:
        return jsonify({"text": f"Photo proof needs attention: {exc}"})
    except photo_proof.PhotoProofError as exc:
        app.logger.exception("Facilities photo proof processing failed")
        return jsonify(
            {
                "text": (
                    "Next Shift could not process the photo proof. "
                    f"The operational issue was not advanced. {exc}"
                )
            }
        )

    if result.get("accepted") is True:
        try:
            fresh = human_reach_runtime._get_delivery(delivery_id)
            human_reach_runtime._refresh_message(fresh)
        except Exception:
            app.logger.exception(
                "Human Reach could not refresh card after photo proof"
            )
        return jsonify({"text": str(result.get("message") or "Photo proof accepted.")})

    return jsonify(
        {
            "text": (
                "Photo proof needs a clearer before/after pair. "
                + str(result.get("message") or "The visible change was not sufficient.")
            )
        }
    )


def chat_event_with_durable_routes():
    event = request.get_json(silent=True)

    if isinstance(event, dict):
        event_type = human_reach_runtime._event_type(event)

        if event_type in {"ADDED_TO_SPACE", "MESSAGE"}:
            try:
                durable_routes.register_space_from_event(event)
            except Exception:
                app.logger.exception(
                    "Human Reach could not persist Google Chat route"
                )

            if event_type == "MESSAGE":
                photo_response = _handle_photo_message(event)
                if photo_response is not None:
                    return photo_response

        elif event_type == "REMOVED_FROM_SPACE":
            try:
                durable_routes.deactivate_space_from_event(event)
            except Exception:
                app.logger.exception(
                    "Human Reach could not deactivate Google Chat route"
                )

    return _original_chat_event()


# main.py registered /chat before this entrypoint loaded. Replace its Flask
# endpoint with the route-aware wrapper and use the same wrapper for the root
# Google Chat callback configured in Cloud Console.
app.view_functions["chat_event"] = chat_event_with_durable_routes
app.add_url_rule(
    "/",
    endpoint="chat_root",
    view_func=chat_event_with_durable_routes,
    methods=["POST"],
)


def readiness():
    try:
        routes = _routes()
        checked_display_names: set[str] = set()

        for owner, display_name in routes.items():
            if display_name in checked_display_names:
                continue

            human_reach_runtime._resolve_space(owner)
            checked_display_names.add(display_name)
    except Exception as exc:
        app.logger.exception(
            "Human Reach readiness failed while resolving durable Chat routes"
        )
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "error": type(exc).__name__,
                }
            ),
            503,
        )

    return jsonify(
        {
            "status": "ready",
            "channel": "google_chat",
            "route_count": len(routes),
            "destination_count": len(checked_display_names),
            "route_source": "state_authority",
            "card_renderer": "cards_v2_rich",
            "facilities_photo_proof": "chat_thread_before_after",
        }
    )


app.add_url_rule(
    "/ready",
    endpoint="human_reach_ready",
    view_func=readiness,
    methods=["GET"],
)
