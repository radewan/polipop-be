class AppException(Exception):
    status_code = 400

    def __init__(self, message: str, field: str | None = None):
        self.message = message
        self.field = field


class NotFound(AppException):
    status_code = 404


class Conflict(AppException):
    status_code = 409


class Unauthorized(AppException):
    status_code = 401


class Forbidden(AppException):
    status_code = 403


class PayloadTooLarge(AppException):
    status_code = 413


class UnsupportedMediaType(AppException):
    status_code = 415


class Unprocessable(AppException):
    status_code = 422
