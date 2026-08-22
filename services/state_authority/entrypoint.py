from human_reach_route_api import blueprint as human_reach_route_blueprint
from main import app


app.register_blueprint(human_reach_route_blueprint)
