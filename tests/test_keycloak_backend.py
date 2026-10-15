import pytest
from pydantic import ValidationError
from starlette.authentication import AuthCredentials
from starlette.requests import Request

from fastapi_keycloak_middleware import (
    AuthorizationMethod,
    FastApiUser,
    KeycloakConfiguration,
    PrincipalType,
    ServicePrincipal,
    get_auth,
)
from fastapi_keycloak_middleware.exceptions import (
    AuthClaimMissing,
    AuthInvalidToken,
    AuthServiceError,
    AuthUserError,
)

pytestmark = pytest.mark.anyio

TOKEN = {
    "sub": "1234",
    "given_name": "Jane",
    "family_name": "Doe",
    "realm_access": {"roles": ["admin", "user"]},
    "scope": "openid profile email",
    "roles": ["flat-role"],
}

SERVICE_TOKEN = {
    "sub": "5678",
    "azp": "svc-keybox",
    "is_device": True,
    "roles": ["keybox"],
}

CLAIM_AUTHORIZATION = {"authorization_method": AuthorizationMethod.CLAIM}


def is_device(claims):
    return bool(claims.get("is_device"))


@pytest.mark.parametrize(
    ("authorization_claim", "expected"),
    [
        ("roles", ["flat-role"]),
        ("realm_access.roles", ["admin", "user"]),
        ("scope", ["openid", "profile", "email"]),
    ],
)
async def test_authorization_claim(make_backend, connection, authorization_claim, expected):
    backend = make_backend(
        TOKEN, config={**CLAIM_AUTHORIZATION, "authorization_claim": authorization_claim}
    )
    context, _ = await backend.authenticate(connection)
    assert context.scopes == expected


async def test_authorization_claim_missing(make_backend, connection):
    backend = make_backend(
        TOKEN,
        config={**CLAIM_AUTHORIZATION, "authorization_claim": "resource_access.my-client.roles"},
    )
    with pytest.raises(AuthClaimMissing):
        await backend.authenticate(connection)


async def test_authorization_claim_invalid_type(make_backend, connection):
    backend = make_backend(
        TOKEN, config={**CLAIM_AUTHORIZATION, "authorization_claim": "realm_access"}
    )
    with pytest.raises(AuthInvalidToken):
        await backend.authenticate(connection)


async def test_authorization_disabled(make_backend, connection):
    context, _ = await make_backend(TOKEN).authenticate(connection)
    assert context.scopes == []


async def test_required_claims(make_backend, connection):
    backend = make_backend(TOKEN, config={"required_claims": ["sub", "realm_access.roles"]})
    await backend.authenticate(connection)

    backend = make_backend(TOKEN, config={"required_claims": ["email"]})
    with pytest.raises(AuthClaimMissing):
        await backend.authenticate(connection)


async def test_sub_is_required_by_default(make_backend, connection):
    token = {key: value for key, value in TOKEN.items() if key != "sub"}
    with pytest.raises(AuthClaimMissing):
        await make_backend(token).authenticate(connection)


async def test_inactive_token_is_rejected(make_backend, connection):
    with pytest.raises(AuthInvalidToken):
        await make_backend({**TOKEN, "active": False}).authenticate(connection)


async def test_user_mapper_receives_all_claims(make_backend, connection):
    received = {}

    async def user_mapper(claims):
        received.update(claims)
        return "user"

    context, user = await make_backend(TOKEN, user_mapper=user_mapper).authenticate(connection)
    assert user == "user"
    assert context.principal_type == PrincipalType.USER
    assert received == {"active": True, **TOKEN}
    assert context.claims == received


async def test_default_user_mapper(make_backend, connection):
    _, user = await make_backend(TOKEN).authenticate(connection)
    assert isinstance(user, FastApiUser)
    assert user.identity == "1234"
    assert user.display_name == "Jane Doe"


@pytest.mark.parametrize("result", [None, RuntimeError("database unavailable")])
async def test_user_mapper_rejects(make_backend, connection, result):
    async def user_mapper(claims):
        if isinstance(result, Exception):
            raise result
        return result

    with pytest.raises(AuthUserError):
        await make_backend(TOKEN, user_mapper=user_mapper).authenticate(connection)


async def test_service_token(make_backend, connection):
    received = {}

    async def service_mapper(claims):
        received.update(claims)
        return claims["azp"]

    async def user_mapper(claims):
        raise AssertionError("user mapper must not be called for service tokens")

    backend = make_backend(
        SERVICE_TOKEN,
        config=CLAIM_AUTHORIZATION,
        user_mapper=user_mapper,
        service_mapper=service_mapper,
        service_detector=is_device,
    )
    context, service = await backend.authenticate(connection)
    assert service == "svc-keybox"
    assert context.principal_type == PrincipalType.SERVICE
    assert context.scopes == ["keybox"]
    assert received["azp"] == "svc-keybox"


async def test_user_token_with_service_detector(make_backend, connection):
    backend = make_backend(TOKEN, service_detector=is_device)
    context, user = await backend.authenticate(connection)
    assert context.principal_type == PrincipalType.USER
    assert isinstance(user, FastApiUser)


async def test_service_token_without_detector_is_user(make_backend, connection):
    context, user = await make_backend(SERVICE_TOKEN).authenticate(connection)
    assert context.principal_type == PrincipalType.USER
    assert isinstance(user, FastApiUser)


@pytest.mark.parametrize(
    ("claims", "client_id"),
    [
        ({"client_id": "from-client-id", "azp": "from-azp"}, "from-client-id"),
        ({"azp": "from-azp"}, "from-azp"),
        ({}, "5678"),
    ],
)
async def test_default_service_mapper(make_backend, connection, claims, client_id):
    token = {"sub": "5678", "is_device": True, **claims}
    _, service = await make_backend(token, service_detector=is_device).authenticate(connection)
    assert isinstance(service, ServicePrincipal)
    assert service.identity == client_id


@pytest.mark.parametrize("result", [None, RuntimeError("client disabled")])
async def test_service_mapper_rejects(make_backend, connection, result):
    async def service_mapper(claims):
        if isinstance(result, Exception):
            raise result
        return result

    backend = make_backend(SERVICE_TOKEN, service_mapper=service_mapper, service_detector=is_device)
    with pytest.raises(AuthServiceError):
        await backend.authenticate(connection)


def test_removed_options_are_rejected():
    with pytest.raises(ValidationError):
        KeycloakConfiguration(
            realm="test",
            url="http://keycloak.invalid",
            client_id="test-client",
            enable_device_authentication=True,
        )


@pytest.mark.parametrize(
    ("scope_auth", "expected"),
    [
        (AuthCredentials(["read", "write"]), ["read", "write"]),
        ("read write", ["read", "write"]),
        (["read write"], ["read write"]),
        (None, []),
    ],
)
async def test_get_auth(scope_auth, expected):
    scope = {"type": "http"}
    if scope_auth is not None:
        scope["auth"] = scope_auth
    assert await get_auth(Request(scope)) == expected
