# 
from flask import Flask
from .llm_client import init_llm
from.routes import register_routes


def create_app() -> Flask:
    app = Flask(__name__)
    init_llm()
    register_routes(app)
    return app