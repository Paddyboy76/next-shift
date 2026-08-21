from flask import jsonify

from main import _resolve_space
from main import _routes
from main import app
from main import chat_event


app.add_url_rule(
    "/",
    endpoint="chat_root",
    view_func=chat_event,
    methods=["POST"],
)


def readiness():
    try:
        routes = _routes()
        resolved = {
            owner: {
                "space": _resolve_space(owner)[0],
                "display_name": display_name,
            }
            for owner, display_name in routes.items()
        }
    except Exception as exc:
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
            "routes": resolved,
        }
    )


app.add_url_rule(
    "/ready",
    endpoint="human_reach_ready",
    view_func=readiness,
    methods=["GET"],
)
