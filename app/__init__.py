import os

from flask import Flask

from config import Config
from app.extensions import db


def create_app(config_class: type = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Garante que as pastas do banco e de backup existam.
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["BACKUP_DIR"], exist_ok=True)

    db.init_app(app)

    from app.routes.registro import registro_bp

    app.register_blueprint(registro_bp)

    with app.app_context():
        db.create_all()

    return app
