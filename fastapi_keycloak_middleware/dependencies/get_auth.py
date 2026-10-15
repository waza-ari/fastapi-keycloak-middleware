"""
This module contains a helper function that can be used as FastAPI dependency
to easily retrieve the resolved permissions for the user
"""

import typing

from fastapi import Request
from starlette.authentication import AuthCredentials


async def get_auth(request: Request) -> typing.List[str]:
    """
    This function can be used as FastAPI dependency to retrieve the authorization
    scopes of the request, after the scope mapper has been applied. Returns an
    empty list if the request has not been authenticated or authorization is disabled.
    """
    auth = request.scope.get("auth")

    if isinstance(auth, AuthCredentials):
        return list(auth.scopes)

    # A string is treated as space delimited list
    if isinstance(auth, str):
        return auth.split()

    return list(auth) if auth else []
