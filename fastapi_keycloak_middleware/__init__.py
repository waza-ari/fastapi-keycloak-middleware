"""
Middleware for FastAPI that supports authenticating users against Keycloak
"""

__version__ = "2.0.0rc1"

import logging

from fastapi_keycloak_middleware.dependencies.check_permission import CheckPermissions
from fastapi_keycloak_middleware.dependencies.get_auth import get_auth
from fastapi_keycloak_middleware.dependencies.principal import (
    get_auth_context,
    get_principal,
    get_service_principal,
    get_user,
)
from fastapi_keycloak_middleware.fast_api_user import FastApiUser
from fastapi_keycloak_middleware.middleware import KeycloakMiddleware
from fastapi_keycloak_middleware.schemas.auth_context import AuthContext
from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)
from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult
from fastapi_keycloak_middleware.schemas.exception_response import ExceptionResponse
from fastapi_keycloak_middleware.schemas.exclude_rule import ExcludeRule
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)
from fastapi_keycloak_middleware.schemas.match_strategy import MatchStrategy
from fastapi_keycloak_middleware.schemas.principal_type import PrincipalType
from fastapi_keycloak_middleware.service_principal import ServicePrincipal
from fastapi_keycloak_middleware.setup import setup_keycloak_middleware

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    AuthContext.__name__,
    AuthorizationResult.__name__,
    ExceptionResponse.__name__,
    ExcludeRule.__name__,
    KeycloakMiddleware.__name__,
    KeycloakConfiguration.__name__,
    AuthorizationMethod.__name__,
    MatchStrategy.__name__,
    PrincipalType.__name__,
    FastApiUser.__name__,
    ServicePrincipal.__name__,
    CheckPermissions.__name__,
    get_auth.__name__,
    get_auth_context.__name__,
    get_principal.__name__,
    get_service_principal.__name__,
    get_user.__name__,
    setup_keycloak_middleware.__name__,
]
