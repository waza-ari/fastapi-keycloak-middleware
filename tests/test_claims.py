import pytest

from fastapi_keycloak_middleware.claims import get_claim, normalize_scopes

TOKEN = {
    "sub": "1234",
    "realm_access": {"roles": ["admin", "user"]},
    "resource_access": {
        "my.client": {"roles": ["client-role"]},
    },
    "https://example.com/roles": ["namespaced"],
    "a.b": "literal",
    "a": {"b": "nested"},
}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("sub", "1234"),
        ("realm_access.roles", ["admin", "user"]),
        ("resource_access.my.client.roles", ["client-role"]),
        ("https://example.com/roles", ["namespaced"]),
        ("realm_access", {"roles": ["admin", "user"]}),
    ],
)
def test_get_claim(path, expected):
    assert get_claim(TOKEN, path) == expected


def test_get_claim_prefers_literal_key():
    assert get_claim(TOKEN, "a.b") == "literal"


def test_get_claim_backtracks_when_literal_path_does_not_resolve():
    claims = {"a.b": {"x": 1}, "a": {"b": {"c": 2}}}
    assert get_claim(claims, "a.b.c") == 2


@pytest.mark.parametrize("path", ["missing", "realm_access.missing", "sub.nested", ""])
def test_get_claim_missing(path):
    with pytest.raises(KeyError):
        get_claim(TOKEN, path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("openid profile  email", ["openid", "profile", "email"]),
        ("single", ["single"]),
        ("", []),
        (["a b", "c"], ["a b", "c"]),
        (None, None),
    ],
)
def test_normalize_scopes(value, expected):
    assert normalize_scopes(value) == expected
