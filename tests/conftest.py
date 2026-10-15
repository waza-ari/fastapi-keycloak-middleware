import typing

import pytest
from starlette.requests import HTTPConnection

from fastapi_keycloak_middleware.keycloak_backend import KeycloakBackend
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)


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
def make_backend(monkeypatch):
    """
    Returns a factory that builds a KeycloakBackend whose token validation
    returns the given claims, without contacting a Keycloak server.
    """

    def _make_backend(token_info: dict[str, typing.Any], user_mapper=None, **config):
        monkeypatch.setattr(
            KeycloakBackend,
            "_get_keycloak_openid",
            lambda self: StubKeycloakOpenID(token_info),
        )
        configuration = KeycloakConfiguration(
            realm="test",
            url="http://keycloak.invalid",
            client_id="test-client",
            use_introspection_endpoint=True,
            **config,
        )
        return KeycloakBackend(keycloak_configuration=configuration, user_mapper=user_mapper)

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
