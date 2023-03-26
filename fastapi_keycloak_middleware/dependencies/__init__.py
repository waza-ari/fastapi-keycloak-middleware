"""
Middleware for FastAPI that supports authenticating users against Keycloak
"""

__version__ = "0.0.1"

from fastapi_keycloak_middleware.middleware import KeycloakMiddleware
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)

__all__ = [KeycloakMiddleware.__name__, KeycloakConfiguration.__name__]
