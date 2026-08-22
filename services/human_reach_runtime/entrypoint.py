from flask import jsonify
from flask import request

from auth import authorize_chat_request
from auth import authorize_pubsub_request
import main as human_reach_runtime
from main import _resolve_space
from main import _routes
from main import app
from main import chat_event
from rich_card import work_card


# Keep the proven delivery/action engine in main.py and replace only the card
# renderer at process startup. main.py resolves _work_card dynamically, so
# proactive sends and in-place CARD_CLICKED updates both use the same Cards v2
# renderer without duplicating workflow logic.
human_reach_runtime._work_card = work_card


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

    return None


app.add_url_rule(
    "/",
    endpoint="chat_root",
    view_func=chat_event,
    methods=["POST"],
)


def readiness():
    try:
        routes = _routes()

        for owner in routes:
            _resolve_space(owner)
    except Exception as exc:
        app.logger.exception(
            "Human Reach readiness failed while resolving Google Chat routes"
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
            "card_renderer": "cards_v2_rich",
        }
    )


app.add_url_rule(
    "/ready",
    endpoint="human_reach_ready",
    view_func=readiness,
    methods=["GET"],
)
