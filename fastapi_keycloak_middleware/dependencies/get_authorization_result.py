"""
This module contains a Dependency that results the authorization result
"""

from typing import Optional
from warnings import warn

from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult


async def get_authorization_result(
    authorization_result: Optional[AuthorizationResult] = None,
):
    """
    This function can be used as FastAPI dependency
    and returns the authorization result
    """
    warn(
        "The decorator method is deprecated and will be removed in the next major version. "
        "Please transition to dependency based permission checking.",
        DeprecationWarning,
        stacklevel=2,
    )
    yield authorization_result
