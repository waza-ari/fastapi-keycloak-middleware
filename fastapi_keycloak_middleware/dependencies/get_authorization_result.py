"""
This module contains a Dependency that results the authorization result
"""

from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult


async def get_authorization_result(
    authorization_result: AuthorizationResult,
) -> AuthorizationResult:
    """
    This function can be used as FastAPI dependency
    and returns the authorization result
    """
    return authorization_result if authorization_result else AuthorizationResult()
