"""
This module contains a Dependency that results the authorization result
"""

from typing import Optional

from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult


async def get_authorization_result(
    authorization_result: Optional[AuthorizationResult] = None,
) -> AuthorizationResult:
    """
    This function can be used as FastAPI dependency
    and returns the authorization result
    """
    yield authorization_result
