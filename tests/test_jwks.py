import asyncio
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwcrypto import jwk, jwt
from jwcrypto.common import JWException
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakConnectionError
from starlette.requests import HTTPConnection

from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware
from fastapi_keycloak_middleware import jwks as jwks_module
from fastapi_keycloak_middleware.exceptions import AuthKeycloakError
from fastapi_keycloak_middleware.jwks import get_token_kid
from fastapi_keycloak_middleware.keycloak_backend import KeycloakBackend

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="module")
def key_1() -> jwk.JWK:
    return jwk.JWK.generate(kty="RSA", size=2048, kid="key-1")


@pytest.fixture(scope="module")
def key_2() -> jwk.JWK:
    return jwk.JWK.generate(kty="RSA", size=2048, kid="key-2")


def public(key: jwk.JWK, use: str = "sig") -> dict:
    return {**key.export_public(as_dict=True), "use": use, "alg": "RS256"}


def sign(key: jwk.JWK, kid: str | None = None, **claims) -> str:
    header = {"alg": "RS256", "kid": kid or key["kid"]}
    token = jwt.JWT(header=header, claims={"sub": "1234", "exp": int(time.time()) + 300, **claims})
    token.make_signed_token(key)
    return token.serialize()


class FakeKeycloakOpenID(KeycloakOpenID):
    """
    KeycloakOpenID with a local certs endpoint. Decoding uses the real implementation.
    """

    def __init__(self):
        super().__init__(server_url="http://keycloak.invalid", realm_name="test", client_id="api")
        self.certs_response: dict | Exception = {"keys": []}
        self.fetches = 0

    async def a_certs(self) -> dict:
        self.fetches += 1
        # Allow other requests to run while the key set is being fetched
        await asyncio.sleep(0)
        if isinstance(self.certs_response, Exception):
            raise self.certs_response
        return self.certs_response

    def certs(self):
        raise AssertionError("The key set must not be fetched synchronously")

    def public_key(self):
        raise AssertionError("The single realm public key must not be used")


@pytest.fixture
def keycloak(monkeypatch, key_1) -> FakeKeycloakOpenID:
    fake = FakeKeycloakOpenID()
    fake.certs_response = {"keys": [public(key_1)]}
    monkeypatch.setattr(KeycloakBackend, "_get_keycloak_openid", lambda self: fake)
    return fake


@pytest.fixture
def clock(monkeypatch):
    """Controls the monotonic clock used for the refresh interval"""

    class Clock:
        now = 1000.0

    monkeypatch.setattr(jwks_module, "monotonic", lambda: Clock.now)
    return Clock


def make_backend(**config) -> KeycloakBackend:
    return KeycloakBackend(
        keycloak_configuration=KeycloakConfiguration(
            realm="test", url="http://keycloak.invalid", client_id="api", **config
        )
    )


def connection(token: str) -> HTTPConnection:
    return HTTPConnection(
        {"type": "http", "headers": [(b"authorization", f"Bearer {token}".encode())]}
    )


async def test_key_set_is_fetched_on_first_request(keycloak, key_1):
    backend = make_backend()
    assert keycloak.fetches == 0

    context, _ = await backend.authenticate(connection(sign(key_1)))
    assert context.claims["sub"] == "1234"
    await backend.authenticate(connection(sign(key_1)))
    assert keycloak.fetches == 1


async def test_rotated_key_is_fetched(keycloak, clock, key_1, key_2):
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))
    clock.now += 3600

    # Keycloak adds a new active key, the previous one stays as passive key
    keycloak.certs_response = {"keys": [public(key_2), public(key_1)]}
    await backend.authenticate(connection(sign(key_2)))
    await backend.authenticate(connection(sign(key_1)))
    assert keycloak.fetches == 2


async def test_rotation_right_after_fetch_is_delayed(keycloak, clock, key_1, key_2):
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))

    # The new key appears within the refresh interval of the last fetch
    clock.now += 10
    keycloak.certs_response = {"keys": [public(key_2), public(key_1)]}
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2)))

    clock.now += 20
    await backend.authenticate(connection(sign(key_2)))
    assert keycloak.fetches == 2


async def test_unknown_key_is_rate_limited(keycloak, clock, key_1, key_2):
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))
    clock.now += 3600

    for _ in range(3):
        with pytest.raises(JWException):
            await backend.authenticate(connection(sign(key_2)))
    # One refetch for the unknown key, the following attempts are rate limited
    assert keycloak.fetches == 2

    clock.now += 30
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2)))
    assert keycloak.fetches == 3


async def test_refresh_interval_is_configurable(keycloak, clock, key_1, key_2):
    backend = make_backend(jwks_refresh_interval=300)
    await backend.authenticate(connection(sign(key_1)))
    clock.now += 3600
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2)))

    clock.now += 60
    keycloak.certs_response = {"keys": [public(key_2)]}
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2)))
    assert keycloak.fetches == 2

    clock.now += 300
    await backend.authenticate(connection(sign(key_2)))
    assert keycloak.fetches == 3


async def test_forged_token_with_known_kid_does_not_refetch(keycloak, key_1, key_2):
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))

    # Signed with another key, but claims to be signed with key-1
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2, kid="key-1")))
    assert keycloak.fetches == 1


async def test_concurrent_requests_fetch_once(keycloak, key_1):
    backend = make_backend()
    await asyncio.gather(*(backend.authenticate(connection(sign(key_1))) for _ in range(5)))
    assert keycloak.fetches == 1


async def test_failed_refetch_keeps_key_set(keycloak, clock, key_1, key_2):
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))
    clock.now += 3600

    keycloak.certs_response = KeycloakConnectionError("connection refused")
    with pytest.raises(JWException):
        await backend.authenticate(connection(sign(key_2)))
    assert keycloak.fetches == 2
    await backend.authenticate(connection(sign(key_1)))


async def test_failed_initial_fetch(keycloak, clock, key_1):
    backend = make_backend()
    keycloak.certs_response = KeycloakConnectionError("connection refused")
    with pytest.raises(AuthKeycloakError):
        await backend.authenticate(connection(sign(key_1)))
    # Failed attempts are rate limited as well
    with pytest.raises(AuthKeycloakError):
        await backend.authenticate(connection(sign(key_1)))
    assert keycloak.fetches == 1

    clock.now += 30
    keycloak.certs_response = {"keys": [public(key_1)]}
    await backend.authenticate(connection(sign(key_1)))


async def test_encryption_and_unsupported_keys_are_skipped(keycloak, key_1, key_2):
    keycloak.certs_response = {
        "keys": [public(key_2, use="enc"), {"kid": "broken", "kty": "unknown"}, public(key_1)]
    }
    backend = make_backend()
    await backend.authenticate(connection(sign(key_1)))

    key_set = await backend.key_set_cache.get_key_set("key-1")
    assert [key["kid"] for key in key_set["keys"]] == ["key-1"]


async def test_key_from_validation_options(keycloak, key_1):
    key = jwk.JWK(**public(key_1))
    backend = make_backend(validation_options={"key": key})
    await backend.authenticate(connection(sign(key_1)))
    assert keycloak.fetches == 0


async def test_no_fetch_without_validation(keycloak, key_2):
    backend = make_backend(validate_token=False)
    context, _ = await backend.authenticate(connection(sign(key_2)))
    assert context.claims["sub"] == "1234"
    assert keycloak.fetches == 0


async def test_check_claims_requires_exp(keycloak, key_1):
    """
    Documents jwcrypto's behaviour: once check_claims is set, the expiry is only
    validated if exp is listed.
    """
    expired = sign(key_1, exp=int(time.time()) - 3600, aud="api")

    backend = make_backend(validation_options={"check_claims": {"aud": "api"}})
    await backend.authenticate(connection(expired))

    backend = make_backend(validation_options={"check_claims": {"aud": "api", "exp": None}})
    with pytest.raises(JWException):
        await backend.authenticate(connection(expired))


def test_keycloak_unreachable_returns_503(keycloak, key_1):
    keycloak.certs_response = KeycloakConnectionError("connection refused")
    app = FastAPI()
    setup_keycloak_middleware(
        app,
        keycloak_configuration=KeycloakConfiguration(
            realm="test", url="http://keycloak.invalid", client_id="api"
        ),
    )
    response = TestClient(app).get("/", headers={"Authorization": f"Bearer {sign(key_1)}"})
    assert response.status_code == 503


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("eyJhbGciOiJSUzI1NiIsImtpZCI6ImFiYyJ9.e30.sig", "abc"),
        ("eyJhbGciOiJSUzI1NiJ9.e30.sig", None),
        ("not-a-token", None),
        ("", None),
        ("WzFd.e30.sig", None),
    ],
)
def test_get_token_kid(token, expected):
    assert get_token_kid(token) == expected
