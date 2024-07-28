"""
This module contains a helper function that can be used as FastAPI dependency
to easily retrieve the user object
"""

from fastapi import Request


async def get_user(request: Request):
    """
    This function can be used as FastAPI dependency
    to easily retrieve the user object
    """
    if "user" in request.scope:
        return request.scope["user"]

    return None
