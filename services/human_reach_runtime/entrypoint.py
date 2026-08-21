from main import app
from main import chat_event


app.add_url_rule(
    "/",
    endpoint="chat_root",
    view_func=chat_event,
    methods=["POST"],
)
