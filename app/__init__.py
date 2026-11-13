"""SVETLANA AI DJ STUDIO – application Flask."""
import secrets as pysecrets

from flask import Flask

from .config import Config
from .pipeline import Pipeline
from .secrets_store import SecretStore
from .storage import Storage


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    if not app.config["SECRET_KEY"]:
        # Pas de clé définie : clé temporaire (sessions perdues au redémarrage,
        # stockage chiffré des clés API désactivé).
        app.config["SECRET_KEY"] = pysecrets.token_hex(32)
        app.config["EPHEMERAL_SECRET"] = True

    data_dir = app.config["DATA_DIR"]
    storage = Storage(data_dir)
    # Les clés API ne sont chiffrables qu'avec une APP_SECRET_KEY stable
    secret_store = SecretStore(data_dir, "" if app.config.get("EPHEMERAL_SECRET") else app.config["SECRET_KEY"])
    pipeline = Pipeline(app.config, storage, secret_store)

    app.extensions["storage"] = storage
    app.extensions["secrets"] = secret_store
    app.extensions["pipeline"] = pipeline

    from .routes import bp
    app.register_blueprint(bp)

    if not app.config.get("TESTING"):
        pipeline.resume_pending()
    return app
