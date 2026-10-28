"""HTTP authentication for remote MCP access."""

import hmac

from starlette.responses import JSONResponse


class BearerTokenMiddleware:
    """Require a configured bearer token for every HTTP request."""

    def __init__(self, app, token: str | None):
        if not token:
            raise ValueError("VISSIM_API_TOKEN must be set for HTTP transport")
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        authorization = next(
            (value for name, value in scope.get("headers", []) if name.lower() == b"authorization"),
            b"",
        ).decode("latin-1")
        scheme, separator, supplied_token = authorization.partition(" ")

        if (
            not separator
            or scheme.lower() != "bearer"
            or not hmac.compare_digest(supplied_token, self.token)
        ):
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)