"""Tests for remote HTTP authentication."""

import pytest
from starlette.testclient import TestClient

from vissim_mcp.auth import BearerTokenMiddleware
from vissim_mcp.server import create_http_app, create_server


@pytest.mark.asyncio
@pytest.mark.parametrize("authorization", [None, b"Basic dXNlcjpwYXNz", b"Bearer wrong"])
async def test_rejects_missing_or_invalid_token(authorization):
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    middleware = BearerTokenMiddleware(app, "expected-token")
    scope = {"type": "http", "headers": []}
    if authorization is not None:
        scope["headers"].append((b"authorization", authorization))
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)

    assert not called
    assert sent[0]["status"] == 401


@pytest.mark.asyncio
async def test_accepts_valid_bearer_token():
    called = False

    async def app(scope, receive, send):
        nonlocal called
        called = True

    middleware = BearerTokenMiddleware(app, "expected-token")
    scope = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer expected-token")],
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        pass

    await middleware(scope, receive, send)

    assert called


def test_requires_token_configuration():
    with pytest.raises(ValueError, match="VISSIM_API_TOKEN"):
        BearerTokenMiddleware(lambda scope, receive, send: None, "")


def test_http_app_rejects_unauthenticated_mcp_request():
    app = create_http_app(create_server("mock", include_ai_tools=False), "expected-token")

    response = TestClient(app).get("/mcp")

    assert response.status_code == 401


def test_http_app_accepts_valid_bearer_token():
    app = create_http_app(create_server("mock", include_ai_tools=False), "expected-token")

    with TestClient(app) as client:
        response = client.get(
            "/mcp",
            headers={"Authorization": "Bearer expected-token"},
        )

    assert response.status_code != 401


@pytest.mark.asyncio
async def test_remote_server_omits_code_execution_tools():
    server = create_server("mock", include_ai_tools=False)
    tools = await server.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "vissim_generate_code" not in tool_names
    assert "vissim_execute_code" not in tool_names