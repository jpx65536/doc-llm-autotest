# 
from flask import Flask
from .llm_client import init_llm
from.routes import register_routes
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app() -> Flask:
    app = Flask(__name__)
    init_llm()
    register_routes(app)
    return app