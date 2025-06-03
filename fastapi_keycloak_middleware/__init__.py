"""
Middleware for FastAPI that supports authenticating users against Keycloak
"""

__version__ = "1.3.0"

import logging

from fastapi_keycloak_middleware.decorators.require_permission import require_permission
from fastapi_keycloak_middleware.decorators.strip_request import strip_request
from fastapi_keycloak_middleware.dependencies.check_permission import CheckPermissions
from fastapi_keycloak_middleware.dependencies.get_auth import get_auth
from fastapi_keycloak_middleware.dependencies.get_authorization_result import (
    get_authorization_result,
)
from fastapi_keycloak_middleware.dependencies.get_user import get_user
from fastapi_keycloak_middleware.fast_api_user import FastApiUser
from fastapi_keycloak_middleware.middleware import KeycloakMiddleware
from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)
from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)
from fastapi_keycloak_middleware.schemas.match_strategy import MatchStrategy
from fastapi_keycloak_middleware.setup import setup_keycloak_middleware

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    AuthorizationResult.__name__,
    KeycloakMiddleware.__name__,
    KeycloakConfiguration.__name__,
    AuthorizationMethod.__name__,
    MatchStrategy.__name__,
    FastApiUser.__name__,
    CheckPermissions.__name__,
    get_auth.__name__,
    get_user.__name__,
    get_authorization_result.__name__,
    require_permission.__name__,
    setup_keycloak_middleware.__name__,
    strip_request.__name__,
]
