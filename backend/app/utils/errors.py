"""Unified JSON error response helpers and custom API exception."""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Structured exception for domain and validation errors."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_response(code: str, message: str, status_code: int = 400):
    """Build standard JSON error payload: { "error": { "code": "...", "message": "..." } }."""
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status_code
    return response


def register_error_handlers(app):
    """Register global error handlers on the Flask app."""

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        return error_response(err.code, err.message, err.status_code)

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
        }
        code = code_map.get(err.code, "HTTP_ERROR")
        return error_response(code, err.description or "HTTP error occurred", err.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err: Exception):
        app.logger.exception("Unhandled exception: %s", err)
        return error_response("INTERNAL_SERVER_ERROR", "An unexpected internal error occurred.", 500)
