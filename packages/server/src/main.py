"""ASGI entrypoint for Frameverse server."""

from src.api.app import create_app

app = create_app()
