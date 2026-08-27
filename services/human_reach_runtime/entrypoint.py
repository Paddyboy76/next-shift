from flask import jsonify
from flask import request

from auth import authorize_chat_request
from auth import authorize_operations_request
from auth import authorize_pubsub_request
import durable_routes
import main as human_reach_runtime
from main import _routes
from main import app
from rich_card import work_card


# Keep the proven delivery/action engine in main.py and replace only the
# integration adapters at process startup. Delivery continues to use the same
# Human Reach engine, while durable route resolution is owned by State
# Authority instead of Google Chat space-list discovery.
human_reach_runtime._work_card = work_card
human_reach_runtime._resolve_space = durable_routes.resolve_space
_original_chat_event = human_reach_runtime.chat_event


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
        }
    )


app.add_url_rule(
    "/ready",
    endpoint="human_reach_ready",
    view_func=readiness,
    methods=["GET"],
)
