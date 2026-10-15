import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient

from fastapi_keycloak_middleware import (
    ExcludeRule,
    KeycloakConfiguration,
    KeycloakMiddleware,
    setup_keycloak_middleware,
)


def http(path: str, method: str = "GET") -> dict:
    return {"type": "http", "path": path, "method": method}


def websocket(path: str) -> dict:
    return {"type": "websocket", "path": path}


@pytest.mark.parametrize(
    ("path", "excluded"),
    [
        ("/status", True),
        # Regression for the unanchored end of the pattern (#3)
        ("/statusboard", False),
        ("/status/admin", False),
        ("/api/status", False),
    ],
)
def test_path_must_match_entirely(path, excluded):
    assert ExcludeRule(path="/status").matches(http(path)) is excluded


def test_path_is_a_regular_expression():
    rule = ExcludeRule(path=r"/users/[0-9]+/avatar")
    assert rule.matches(http("/users/42/avatar"))
    assert not rule.matches(http("/users/me/avatar"))
    assert not rule.matches(http("/users/42/avatar/edit"))


def test_explicit_anchors_keep_working():
    rule = ExcludeRule(path=r"^/hook/.+$")
    assert rule.matches(http("/hook/payment"))
    assert not rule.matches(http("/hook/"))


@pytest.mark.parametrize(
    ("prefix", "path", "excluded"),
    [
        ("/docs", "/docs", True),
        ("/docs", "/docs/oauth2-redirect", True),
        ("/docs", "/docs-admin", False),
        ("/docs", "/doc", False),
        ("/api/external/", "/api/external", True),
        ("/api/external/", "/api/external/orders/1", True),
        ("/api/external/", "/api/externals", False),
        ("/", "/anything", True),
    ],
)
def test_prefix_matches_whole_segments(prefix, path, excluded):
    assert ExcludeRule(prefix=prefix).matches(http(path)) is excluded


def test_methods():
    rule = ExcludeRule(path="/register", methods=["post"])
    assert rule.matches(http("/register", "POST"))
    assert not rule.matches(http("/register", "GET"))
    assert not rule.matches(http("/other", "POST"))


def test_get_includes_head():
    rule = ExcludeRule(path="/status", methods={"GET"})
    assert rule.matches(http("/status", "HEAD"))
    assert not ExcludeRule(path="/status", methods={"POST"}).matches(http("/status", "HEAD"))


def test_methods_only_rule_matches_every_path():
    rule = ExcludeRule(methods={"OPTIONS"})
    assert rule.matches(http("/anything/at/all", "OPTIONS"))
    assert not rule.matches(http("/anything/at/all", "GET"))


def test_websockets():
    assert ExcludeRule(path="/ws").matches(websocket("/ws"))
    assert ExcludeRule(prefix="/ws").matches(websocket("/ws/chat"))
    # Websocket connections have no method, so rules with methods never match
    assert not ExcludeRule(path="/ws", methods={"GET"}).matches(websocket("/ws"))


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"methods": []},
        {"path": "/a", "prefix": "/a"},
        {"path": "("},
        {"prefix": "docs"},
    ],
)
def test_invalid_rules(kwargs):
    with pytest.raises(ValueError):
        ExcludeRule(**kwargs)


def make_app(exclude_patterns) -> TestClient:
    app = FastAPI()
    setup_keycloak_middleware(
        app,
        keycloak_configuration=KeycloakConfiguration(
            realm="test", url="http://keycloak.invalid", client_id="api"
        ),
        exclude_patterns=exclude_patterns,
    )

    @app.api_route("/status", methods=["GET", "POST"])
    @app.get("/statusboard")
    @app.get("/docs/oauth2-redirect")
    @app.get("/docs-admin")
    async def endpoint():
        return {"ok": True}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.close()

    return TestClient(app)


def test_middleware_applies_rules():
    client = make_app(
        [
            "/statusboard",
            ExcludeRule(path="/status", methods={"GET"}),
            ExcludeRule(prefix="/docs"),
            ExcludeRule(path="/ws"),
        ]
    )
    # No token is sent, so every request that is not excluded is rejected
    assert client.get("/status").status_code == 200
    # Passes the middleware, FastAPI routes don't answer HEAD themselves
    assert client.head("/status").status_code == 405
    assert client.post("/status").status_code == 401
    assert client.get("/statusboard").status_code == 200
    assert client.get("/docs/oauth2-redirect").status_code == 200
    assert client.get("/docs-admin").status_code == 401
    with client.websocket_connect("/ws"):
        pass


def test_string_patterns_no_longer_match_prefixes():
    client = make_app(["/status"])
    assert client.get("/status").status_code == 200
    assert client.get("/statusboard").status_code == 401


def test_invalid_pattern_fails_at_startup():
    config = KeycloakConfiguration(realm="test", url="http://keycloak.invalid", client_id="api")
    with pytest.raises(ValueError):
        KeycloakMiddleware(app=FastAPI(), keycloak_configuration=config, exclude_patterns=["("])
