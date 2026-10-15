import typing

import pytest
from fastapi import Depends, FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.requests import HTTPConnection

from fastapi_keycloak_middleware import (
    KeycloakConfiguration,
    get_auth,
    get_user,
    setup_keycloak_middleware,
)
from fastapi_keycloak_middleware.keycloak_backend import KeycloakBackend


@pytest.fixture
def anyio_backend():
    return "asyncio"


class StubKeycloakOpenID:
    """Stands in for KeycloakOpenID, the introspection endpoint returns fixed claims"""

    def __init__(self, token_info: dict[str, typing.Any]):
        self.token_info = token_info

    async def a_introspect(self, token: str) -> dict[str, typing.Any]:
        return self.token_info


@pytest.fixture
def stub_keycloak(monkeypatch):
    """
    Returns a function that makes every KeycloakBackend created afterwards
    validate tokens against the given claims, without contacting a Keycloak server.
    """

    def _stub(token_info: dict[str, typing.Any]):
        monkeypatch.setattr(
            KeycloakBackend,
            "_get_keycloak_openid",
            lambda self: StubKeycloakOpenID(token_info),
        )

    return _stub


def make_configuration(**config) -> KeycloakConfiguration:
    return KeycloakConfiguration(
        **{
            "realm": "test",
            "url": "http://keycloak.invalid",
            "client_id": "test-client",
            "use_introspection_endpoint": True,
            **config,
        }
    )


@pytest.fixture
def make_backend(stub_keycloak):
    """Returns a factory that builds a KeycloakBackend validating tokens to the given claims"""

    def _make_backend(token_info: dict[str, typing.Any], user_mapper=None, **config):
        stub_keycloak(token_info)
        return KeycloakBackend(
            keycloak_configuration=make_configuration(**config), user_mapper=user_mapper
        )

    return _make_backend


@pytest.fixture
def connection() -> HTTPConnection:
    return HTTPConnection(
        {
            "type": "http",
            "path": "/",
            "headers": [(b"authorization", b"Bearer token")],
        }
    )


@pytest.fixture
def make_client(stub_keycloak):
    """
    Returns a factory that builds a TestClient for an app protected by the middleware.

    The app exposes ``/me`` returning what the dependencies resolved, ``/public``
    which is excluded from authentication and a ``/ws`` websocket endpoint.
    """

    def _make_client(
        token_info: dict[str, typing.Any], config: dict | None = None, **middleware
    ) -> TestClient:
        stub_keycloak(token_info)
        app = FastAPI()
        setup_keycloak_middleware(
            app,
            keycloak_configuration=make_configuration(**(config or {})),
            exclude_patterns=["^/public$"],
            **middleware,
        )

        @app.get("/me")
        async def me(user=Depends(get_user), auth=Depends(get_auth)):
            return {"user": str(user), "auth": auth}

        @app.get("/public")
        async def public():
            return {"public": True}

        @app.websocket("/ws")
        async def ws(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"user": str(websocket.scope.get("user"))})
            await websocket.close()

        return TestClient(app)

    return _make_client
