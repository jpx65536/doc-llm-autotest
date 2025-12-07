# 
from flask import Flask
from .llm.llm_client import init_llm
from.routes import bp as main_bp
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> Flask:
    app = Flask(__name__)
    init_llm()
    app.register_blueprint(main_bp)
    return app