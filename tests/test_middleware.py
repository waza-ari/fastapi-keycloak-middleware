import pytest
from keycloak.exceptions import KeycloakConnectionError
from starlette.websockets import WebSocketDisconnect

from fastapi_keycloak_middleware import AuthorizationMethod

TOKEN = {
    "sub": "1234",
    "name": "Jane Doe",
    "given_name": "Jane",
    "family_name": "Doe",
    "preferred_username": "jane",
    "email": "jane@example.com",
    "roles": ["admin"],
}

SERVICE_TOKEN = {
    "sub": "5678",
    "azp": "svc-keybox",
    "is_device": True,
    "roles": ["admin"],
}

AUTH_HEADER = {"Authorization": "Bearer token"}
CLAIM_AUTHORIZATION = {"authorization_method": AuthorizationMethod.CLAIM}


async def map_user(claims):
    return claims["preferred_username"]


async def map_service(claims):
    return f"service:{claims['azp']}"


def is_device(claims):
    return bool(claims.get("is_device"))


@pytest.fixture
def make_service_client(make_client):
    def _make(token, **middleware):
        return make_client(
            token,
            config=CLAIM_AUTHORIZATION,
            user_mapper=map_user,
            service_mapper=map_service,
            service_detector=is_device,
            **middleware,
        )

    return _make


def test_missing_header(make_client):
    response = make_client(TOKEN).get("/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Your request is missing an 'Authorization' HTTP header"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_wrong_scheme(make_client):
    response = make_client(TOKEN).get("/me", headers={"Authorization": "Token token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Unable to verify provided access token"}
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


def test_custom_scheme_challenge(make_client):
    client = make_client(TOKEN, config={"authentication_scheme": "Token"})
    response = client.get("/me", headers={"Authorization": "Token token"})
    assert response.status_code == 200
    response = client.get("/me", headers={"Authorization": "Bearer token"})
    assert response.headers["WWW-Authenticate"] == 'Token error="invalid_token"'


def test_inactive_token(make_client):
    response = make_client({**TOKEN, "active": False}).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 401
    assert response.json() == {"detail": "Unable to verify provided access token"}


def test_keycloak_unreachable(make_client):
    response = make_client(KeycloakConnectionError("connection refused")).get(
        "/me", headers=AUTH_HEADER
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Unable to reach the identity provider"}
    assert "WWW-Authenticate" not in response.headers


def test_excluded_path(make_client):
    response = make_client(TOKEN).get("/public")
    assert response.status_code == 200


def test_excluded_path_has_no_principal(make_client):
    response = make_client(TOKEN).get("/public/principal")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_authenticated(make_client):
    async def scope_mapper(scopes):
        return [f"mapped:{scope}" for scope in scopes]

    client = make_client(
        TOKEN,
        config=CLAIM_AUTHORIZATION,
        user_mapper=map_user,
        scope_mapper=scope_mapper,
    )
    response = client.get("/me", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"user": "jane", "auth": ["mapped:admin"]}


def test_auth_context(make_client):
    async def scope_mapper(scopes):
        return [f"mapped:{scope}" for scope in scopes]

    client = make_client(TOKEN, config=CLAIM_AUTHORIZATION, scope_mapper=scope_mapper)
    response = client.get("/context", headers=AUTH_HEADER)
    assert response.json() == {
        "principal_type": "user",
        "claims": {"active": True, **TOKEN},
        "scopes": ["mapped:admin"],
        "request_auth": ["mapped:admin"],
    }


@pytest.mark.parametrize("result", ["none", "raise"])
def test_user_mapper_rejects(make_client, result):
    async def user_mapper(claims):
        if result == "raise":
            raise RuntimeError("database unavailable")
        return None

    response = make_client(TOKEN, user_mapper=user_mapper).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not find a user based on this token"}


def test_missing_claim(make_client):
    token = {key: value for key, value in TOKEN.items() if key != "sub"}
    response = make_client(token).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 401
    assert response.json() == {"detail": "The access token is missing the claim 'sub'"}
    assert response.headers["WWW-Authenticate"] == 'Bearer error="invalid_token"'


def test_service_principal(make_service_client):
    client = make_service_client(SERVICE_TOKEN)

    response = client.get("/principal", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"principal": "service:svc-keybox", "auth": ["admin"]}

    response = client.get("/service", headers=AUTH_HEADER)
    assert response.json() == {"service": "service:svc-keybox"}

    response = client.get("/context", headers=AUTH_HEADER)
    assert response.json()["principal_type"] == "service"


def test_service_principal_on_user_endpoint(make_service_client):
    response = make_service_client(SERVICE_TOKEN).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 403


def test_user_on_service_endpoint(make_service_client):
    client = make_service_client(TOKEN)
    assert client.get("/service", headers=AUTH_HEADER).status_code == 403
    assert client.get("/principal", headers=AUTH_HEADER).json()["principal"] == "jane"


@pytest.mark.parametrize("result", ["none", "raise"])
def test_service_mapper_rejects(make_client, result):
    async def service_mapper(claims):
        if result == "raise":
            raise RuntimeError("client disabled")
        return None

    client = make_client(SERVICE_TOKEN, service_mapper=service_mapper, service_detector=is_device)
    response = client.get("/principal", headers=AUTH_HEADER)
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not find a service based on this token"}


@pytest.mark.parametrize("token", [TOKEN, SERVICE_TOKEN])
def test_check_permissions_for_both_principal_types(make_service_client, token):
    response = make_service_client(token).get("/admin", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"matched": ["admin"]}


def test_check_permissions_denied(make_service_client):
    token = {**TOKEN, "roles": ["user"]}
    response = make_service_client(token).get("/admin", headers=AUTH_HEADER)
    assert response.status_code == 403


def test_check_permissions_without_authorization(make_client):
    response = make_client(TOKEN).get("/admin", headers=AUTH_HEADER)
    assert response.status_code == 403


def test_websocket_cookie(make_client):
    client = make_client(TOKEN, user_mapper=map_user)
    client.cookies.set("access_token", "Bearer token")
    with client.websocket_connect("/ws") as websocket:
        assert websocket.receive_json() == {"user": "jane"}


def test_websocket_without_cookie(make_client):
    client = make_client(TOKEN, user_mapper=map_user)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws"):
            pass


def test_websocket_support_disabled(make_client):
    client = make_client(TOKEN, config={"enable_websocket_support": False})
    with client.websocket_connect("/ws") as websocket:
        assert websocket.receive_json() == {"user": "None"}
