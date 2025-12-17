from flask import Flask
from flask_socketio import SocketIO
from mongoengine import connect
from config import Config
import os
import certifi

socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    # Get the base directory (project root)
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static"),
    )
    app.config.from_object(Config)

    # Connect to MongoDB (Atlas with TLS CA file)
    connect(
        db=app.config["MONGODB_SETTINGS"]["db"],
        host=app.config["MONGODB_SETTINGS"]["host"],
        tlsCAFile=certifi.where(),
    )

    # Initialize SocketIO
    socketio.init_app(app)

    # Register blueprints
    from app.auth import auth_bp

    app.register_blueprint(auth_bp)

    from app.groups import groups_bp

    app.register_blueprint(groups_bp)

    from app.tasks import tasks_bp

    app.register_blueprint(tasks_bp)

    # Register SocketIO event handlers
    from app import socketio_events

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template

        return render_template("errors/404.html"), 404

    return app
