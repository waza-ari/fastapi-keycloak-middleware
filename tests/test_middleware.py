import pytest
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

AUTH_HEADER = {"Authorization": "Bearer token"}


async def map_user(userinfo):
    return userinfo["preferred_username"]


def test_missing_header(make_client):
    response = make_client(TOKEN).get("/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Your request is missing an 'Authorization' HTTP header"}


def test_wrong_scheme(make_client):
    response = make_client(TOKEN).get("/me", headers={"Authorization": "Token token"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Unable to verify provided access token"}


def test_excluded_path(make_client):
    response = make_client(TOKEN).get("/public")
    assert response.status_code == 200


def test_authenticated(make_client):
    async def scope_mapper(scopes):
        return [f"mapped:{scope}" for scope in scopes]

    client = make_client(
        TOKEN,
        config={"authorization_method": AuthorizationMethod.CLAIM},
        user_mapper=map_user,
        scope_mapper=scope_mapper,
    )
    response = client.get("/me", headers=AUTH_HEADER)
    assert response.status_code == 200
    assert response.json() == {"user": "jane", "auth": ["mapped:admin"]}


@pytest.mark.parametrize("result", ["none", "raise"])
def test_user_mapper_rejects(make_client, result):
    async def user_mapper(userinfo):
        if result == "raise":
            raise RuntimeError("database unavailable")
        return None

    response = make_client(TOKEN, user_mapper=user_mapper).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 401
    assert response.json() == {"detail": "Could not find a user based on this token"}


def test_missing_claim(make_client):
    token = {key: value for key, value in TOKEN.items() if key != "email"}
    response = make_client(token).get("/me", headers=AUTH_HEADER)
    assert response.status_code == 401


def test_websocket_cookie(make_client):
    client = make_client(TOKEN, user_mapper=map_user)
    client.cookies.set("access_token", "Bearer token")
    with client.websocket_connect("/ws", headers={"upgrade": "websocket"}) as websocket:
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
