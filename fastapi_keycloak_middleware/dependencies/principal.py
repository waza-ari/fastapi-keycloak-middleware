"""
This module contains FastAPI dependencies to retrieve the authenticated principal
and the authentication context from the request.
"""

import typing

from fastapi import HTTPException, Request

from fastapi_keycloak_middleware.schemas.auth_context import AuthContext
from fastapi_keycloak_middleware.schemas.principal_type import PrincipalType


def _unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Request is not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_auth_context(request: Request) -> AuthContext:
    """
    This function can be used as FastAPI dependency to retrieve the authentication
    context, holding the principal type, all token claims and the authorization scopes.

    Raises a 401 error if the request has not been authenticated, e.g. because
    the path is excluded from authentication.
    """
    auth_context = request.scope.get("auth_context")
    if not isinstance(auth_context, AuthContext):
        raise _unauthenticated()
    return auth_context


async def _get_principal_of_type(
    request: Request, principal_type: PrincipalType | None
) -> typing.Any:
    auth_context = await get_auth_context(request)
    principal = request.scope.get("user")
    if principal is None:
        raise _unauthenticated()
    if principal_type is not None and auth_context.principal_type != principal_type:
        raise HTTPException(status_code=403, detail="Permission denied")
    return principal


async def get_principal(request: Request) -> typing.Any:
    """
    This function can be used as FastAPI dependency to retrieve the authenticated
    principal, i.e. the object returned by either the user or the service mapper.

    Raises a 401 error if the request has not been authenticated.
    """
    return await _get_principal_of_type(request, None)


async def get_user(request: Request) -> typing.Any:
    """
    This function can be used as FastAPI dependency to retrieve the user object
    returned by the user mapper.

    Raises a 401 error if the request has not been authenticated and a 403 error
    if the token was issued to a service.
    """
    return await _get_principal_of_type(request, PrincipalType.USER)


async def get_service_principal(request: Request) -> typing.Any:
    """
    This function can be used as FastAPI dependency to retrieve the service object
    returned by the service mapper.

    Raises a 401 error if the request has not been authenticated and a 403 error
    if the token was issued to a user.
    """
    return await _get_principal_of_type(request, PrincipalType.SERVICE)
