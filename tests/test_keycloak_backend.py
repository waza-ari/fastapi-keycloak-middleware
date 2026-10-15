import pytest
from starlette.requests import Request

from fastapi_keycloak_middleware import AuthorizationMethod, get_auth
from fastapi_keycloak_middleware.exceptions import AuthClaimMissing

pytestmark = pytest.mark.anyio

TOKEN = {
    "sub": "1234",
    "given_name": "Jane",
    "family_name": "Doe",
    "realm_access": {"roles": ["admin", "user"]},
    "scope": "openid profile email",
    "roles": ["flat-role"],
}


async def test_authorization_claim_top_level(make_backend, connection):
    backend = make_backend(TOKEN, claims=["sub"], authorization_method=AuthorizationMethod.CLAIM)
    auth, _ = await backend.authenticate(connection)
    assert auth == ["flat-role"]


async def test_authorization_claim_nested(make_backend, connection):
    backend = make_backend(
        TOKEN,
        claims=["sub"],
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="realm_access.roles",
    )
    auth, _ = await backend.authenticate(connection)
    assert auth == ["admin", "user"]


async def test_authorization_claim_space_delimited(make_backend, connection):
    backend = make_backend(
        TOKEN,
        claims=["sub"],
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="scope",
    )
    auth, _ = await backend.authenticate(connection)
    assert auth == ["openid", "profile", "email"]


async def test_authorization_claim_missing_nested(make_backend, connection):
    backend = make_backend(
        TOKEN,
        claims=["sub"],
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="resource_access.my-client.roles",
    )
    with pytest.raises(AuthClaimMissing):
        await backend.authenticate(connection)


async def test_nested_claims_reach_user_mapper(make_backend, connection):
    received = {}

    async def user_mapper(userinfo):
        received.update(userinfo)
        return "user"

    backend = make_backend(TOKEN, user_mapper=user_mapper, claims=["sub", "realm_access.roles"])
    auth, user = await backend.authenticate(connection)
    assert user == "user"
    assert auth is None
    assert received == {"sub": "1234", "realm_access.roles": ["admin", "user"]}


async def test_device_token_with_nested_authorization_claim(make_backend, connection):
    backend = make_backend(
        {**TOKEN, "is_device": True},
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="realm_access.roles",
        enable_device_authentication=True,
    )
    auth, user = await backend.authenticate(connection)
    assert auth == ["admin", "user"]
    assert user is None


@pytest.mark.parametrize(
    ("scope_auth", "expected"),
    [
        ("read write", ["read", "write"]),
        (["read write"], ["read write"]),
    ],
)
async def test_get_auth_splits_strings(scope_auth, expected):
    request = Request({"type": "http", "auth": scope_auth})
    assert await get_auth(request) == expected
