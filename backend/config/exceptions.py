from rest_framework.views import exception_handler


def _flatten(detail):
    if isinstance(detail, dict):
        parts = []
        for key, value in detail.items():
            text = _flatten(value)
            parts.append(text if key in ("detail", "non_field_errors") else f"{key}: {text}")
        return "；".join(parts)
    if isinstance(detail, list):
        return "；".join(_flatten(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    message = _flatten(response.data)
    response.data = {"code": response.status_code, "message": message, "data": None}
    return response
