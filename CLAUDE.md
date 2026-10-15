# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`fastapi-keycloak-middleware` is a library (published to PyPI) that adds Keycloak/OIDC authentication and claim-based authorization to FastAPI apps. Python >=3.11, managed with Poetry. Its runtime dependencies are only `fastapi` and `python-keycloak` (the `python-keycloak` range is pinned deliberately: `>=4.7.3,!=7.0.0,<8`; 4.7.3 is the first release compatible with `httpx` 0.28, and CI tests that minimum in a separate job, so bump both together). User docs live in `docs/` (Sphinx, published on Read the Docs).

## Commands

```bash
poetry install --with dev        # install package + dev deps (sphinx, ruff)
ruff check .                     # lint (ruff config in pyproject.toml; fix = true, line-length 100)
ruff format .                    # format
pre-commit run --all-files       # what CI runs (.github/workflows/python-lint.yml)
cd docs && make html             # build docs; RTD builds with fail_on_warning: true
poetry run pytest                # run tests
poetry run pytest tests/test_claims.py::test_get_claim_prefers_literal_key   # single test
```

Tests live in `tests/` and need no Keycloak server: the `make_backend` fixture in `tests/conftest.py` stubs `KeycloakOpenID` with fixed token claims. Async tests use the AnyIO pytest plugin (`pytestmark = pytest.mark.anyio`). CI runs pre-commit (ruff, ruff-format, pyupgrade, yaml/whitespace checks) and the tests on Python 3.11–3.14. `docs/testing.rst` documents how *consumers* test their apps with this middleware. It is not a guide for testing this library.

## Releasing

The version string is duplicated in three places, and all three must be bumped together:
- `pyproject.toml` (`version`)
- `fastapi_keycloak_middleware/__init__.py` (`__version__`)
- `docs/conf.py` (`release`)

Pushing a `vX.Y.Z` tag triggers `.github/workflows/release.yml`, which publishes to TestPyPI and PyPI via `JRubics/poetry-publish`. Commit messages follow Conventional Commits (`fix:`, `chore:`, `docs:`, `build:`); breaking changes use `!` and a `BREAKING CHANGE:` footer, and belong in `docs/migration_v2.rst` while 2.0 is unreleased.

## Architecture

Request flow: `setup_keycloak_middleware()` → `KeycloakMiddleware` (raw ASGI) → `KeycloakBackend.authenticate()` → results stored in the ASGI scope → read back by dependencies.

- **`setup.py`**: `setup_keycloak_middleware()` is the main entry point. It adds the middleware, and it can also inject 401/403 responses into the app router's OpenAPI responses and register an `OpenIdConnect` security dependency on `app.router` for Swagger UI auth. Users can also add `KeycloakMiddleware` directly with `app.add_middleware`.
- **`middleware.py`**: `KeycloakMiddleware` is a plain ASGI callable, not Starlette's `AuthenticationMiddleware`. It skips non-HTTP scopes (websockets are checked only when `enable_websocket_support` is set) and paths that match `exclude_patterns` (regexes, matched with `re.match` against `scope["path"]`). It runs the async `scope_mapper` on the scopes and sets `scope["user"]` (the principal), `scope["auth"]` (Starlette `AuthCredentials`) and `scope["auth_context"]` (`AuthContext`). Backend exceptions become 401 responses with a `WWW-Authenticate` challenge (RFC 6750); `AuthKeycloakError` becomes a 503.
- **`keycloak_backend.py`**: `KeycloakBackend` builds a `KeycloakOpenID` client at construction time but makes no network call there. `authenticate()` returns `(AuthContext, principal)`, in this order:
  1. Read the token from the `Authorization` header, or from a cookie (`websocket_cookie_name`) on websocket connections.
  2. Validate it locally (`a_decode_token` with the key set from `jwks.KeySetCache`, or a `key` from `validation_options`) or by introspection (`a_introspect`; inactive tokens are rejected).
  3. Check `required_claims`.
  4. Classify the token as `PrincipalType.USER` or `SERVICE` with the optional `service_detector`; without a detector, every token is a user.
  5. Extract scopes from `authorization_claim` (only for `AuthorizationMethod.CLAIM`, otherwise `[]`).
  6. Call `user_mapper` or `service_mapper` with **all** claims. `None` or an exception rejects the request (`AuthUserError` / `AuthServiceError`). The defaults return `FastApiUser` / `ServicePrincipal`.

  Claim lookups go through `claims.get_claim()`, which resolves dotted paths (a literal key wins). `normalize_scopes()` splits space-delimited strings.
- **`jwks.py`**: `KeySetCache` lazily fetches the realm JWKS (`a_certs()`, signing keys only) on the first request. It refetches only when the token header's `kid` is missing from the cache, at most once per `jwks_refresh_interval`; failed attempts count, and the old set is kept. The decision is based on the `kid`, never on jwcrypto's `JWKeyNotFound`, which is also raised for a known `kid` with a bad signature. The clock is the module-level `monotonic` import, so tests patch `jwks.monotonic`, not `time.monotonic`, which asyncio uses.
- **`schemas/keycloak_configuration.py`**: `KeycloakConfiguration` (Pydantic v2, `extra="forbid"`) holds every backend option. A new option goes here, gets documented in the class docstring (the Sphinx autodoc source), and is then used in the backend or middleware. Callables (mappers, detector) are arguments of `setup_keycloak_middleware` / `KeycloakMiddleware`, not configuration fields.
- **`dependencies/`**: `principal.py` has `get_principal`, `get_user` (403 for services), `get_service_principal` (403 for users) and `get_auth_context`; all respond with 401 when the request is unauthenticated. `get_auth` returns the scopes as a list. `CheckPermissions(required_permission, match_strategy)` is a callable class used as `Depends(CheckPermissions(...))`. It returns an `AuthorizationResult` or raises a 403. It deliberately depends **only on `get_auth`**, so consumers can override `get_auth` in tests with the middleware mocked away. Don't add principal dependencies to it.
- **`exceptions.py`**: internal `Auth*` exceptions raised by the backend and translated to HTTP responses by the middleware.

Public API is whatever is re-exported in `fastapi_keycloak_middleware/__init__.py` (`__all__`). Keep it in sync when adding public symbols, and document them in `docs/api.rst`.

## Conventions

- Logging goes through module-level `log = logging.getLogger(__name__)`. The package installs a `NullHandler`. Use `%`-style lazy log arguments in new code; some older files use f-strings.
- Ruff ignores `UP006`/`UP007`, so `typing.List`, `typing.Dict`, and `typing.Union` are used throughout alongside `X | None`. Match the style of the surrounding file.
- Docstrings use Sphinx `:param:` / `:type:` fields, because they feed the autodoc API reference.
