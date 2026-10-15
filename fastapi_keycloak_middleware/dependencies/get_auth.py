"""
This module contains a helper function that can be used as FastAPI dependency
to easily retrieve the resolved permissions for the user
"""

from fastapi import Request


async def get_auth(request: Request):
    """
    This function can be used as FastAPI dependency
    to easily retrieve the user object
    """
    if "auth" in request.scope:
        auth = request.scope["auth"]

        # A string (e.g. returned by a scope mapper) is treated as space delimited list
        if isinstance(auth, str):
            return auth.split()

        return auth

    return None
