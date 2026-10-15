# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`fastapi-keycloak-middleware` is a library (published to PyPI) that adds Keycloak/OIDC authentication and claim-based authorization to FastAPI apps. Python >=3.11, managed with Poetry. Its runtime dependencies are only `fastapi` and `python-keycloak` (the `python-keycloak` range is pinned deliberately: `>=4.1,!=7.0.0,<8`). User docs live in `docs/` (Sphinx, published on Read the Docs).

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

Tests live in `tests/` and need no Keycloak server: the `make_backend` fixture in `tests/conftest.py` stubs `KeycloakOpenID` with fixed token claims. Async tests use the AnyIO pytest plugin (`pytestmark = pytest.mark.anyio`). CI does not run tests yet; it only runs pre-commit (ruff, ruff-format, pyupgrade, yaml/whitespace checks). `docs/testing.rst` documents how *consumers* test their apps with this middleware. It is not a guide for testing this library.

## Releasing

The version string is duplicated in three places, and all three must be bumped together:
- `pyproject.toml` (`version`)
- `fastapi_keycloak_middleware/__init__.py` (`__version__`)
- `docs/conf.py` (`release`)

Pushing a `vX.Y.Z` tag triggers `.github/workflows/release.yml`, which publishes to TestPyPI and PyPI via `JRubics/poetry-publish`. Commit messages follow Conventional Commits (`fix:`, `chore:`, `docs:`, `build:`).

## Architecture

Request flow: `setup_keycloak_middleware()` → `KeycloakMiddleware` (raw ASGI) → `KeycloakBackend.authenticate()` → results stored in the ASGI scope → read back by dependencies.

- **`setup.py`**: `setup_keycloak_middleware()` is the main entry point. It adds the middleware, and it can also inject 401/403 responses into the app router's OpenAPI responses and register an `OpenIdConnect` security dependency on `app.router` for Swagger UI auth. Users can also add `KeycloakMiddleware` directly with `app.add_middleware`.
- **`middleware.py`**: `KeycloakMiddleware` is a plain ASGI callable, not Starlette's `AuthenticationMiddleware`. It skips non-HTTP scopes (websockets are checked only when `enable_websocket_support` is set) and paths that match `exclude_patterns` (regexes, matched with `re.match` against `scope["path"]`). It maps backend exceptions to 401 JSON responses, optionally runs the async `scope_mapper` on the auth scopes, and sets `scope["auth"]` and `scope["user"]`.
- **`keycloak_backend.py`**: `KeycloakBackend` builds a `KeycloakOpenID` client at construction time. Unless `use_introspection_endpoint` is set, it also **fetches the realm public key synchronously in `__init__`**, so constructing the middleware makes a network call to Keycloak. The token comes from the `Authorization` header, or from a cookie (`websocket_cookie_name`) on websocket upgrades. The backend validates the token locally (`a_decode_token`) or by introspection (`a_introspect`), extracts the configured `claims` into a dict, and passes that dict to the async `user_mapper`. The default mapper returns a `FastApiUser`. Two behaviors are easy to miss:
  - Authorization scopes come from `authorization_claim` only when `authorization_method == AuthorizationMethod.CLAIM`. Otherwise `auth` is `None`. Claim lookups go through `claims.get_claim()`, which resolves dotted paths (a literal key wins), and `normalize_scopes()` splits space-delimited strings.
  - Device authentication: if it is enabled and the device claim is truthy, the backend skips user mapping and returns `(auth, None)`, so `scope["user"]` is `None`.
- **`schemas/keycloak_configuration.py`**: `KeycloakConfiguration` (Pydantic v2) holds every backend option. A new option goes here, gets documented in the class docstring (the Sphinx autodoc source), and is then used in the backend or middleware.
- **`dependencies/`**: `get_user` and `get_auth` read `request.scope["user"]` / `request.scope["auth"]`. `CheckPermissions(required_permission, match_strategy)` is the **current, preferred** authorization API. It is a callable class used as `Depends(CheckPermissions(...))`. It returns an `AuthorizationResult` or raises a 403.
- **`decorators/`**: `require_permission` is **deprecated** (it emits `DeprecationWarning`), and so is the `get_authorization_result` dependency. The decorator rewrites the endpoint's signature to inject a `request` parameter, and `strip_request` removes that parameter again before calling the original function. Don't build new features on the decorator path.
- **`exceptions.py`**: internal `Auth*` exceptions raised by the backend and translated to HTTP responses by the middleware.

Public API is whatever is re-exported in `fastapi_keycloak_middleware/__init__.py` (`__all__`). Keep it in sync when adding public symbols, and document them in `docs/api.rst`.

## Conventions

- Logging goes through module-level `log = logging.getLogger(__name__)`. The package installs a `NullHandler`. Use `%`-style lazy log arguments in new code; some older files use f-strings.
- Ruff ignores `UP006`/`UP007`, so `typing.List`, `typing.Dict`, and `typing.Union` are used throughout alongside `X | None`. Match the style of the surrounding file.
- Docstrings use Sphinx `:param:` / `:type:` fields, because they feed the autodoc API reference.
