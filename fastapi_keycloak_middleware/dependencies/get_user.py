"""
This module contains a helper function
that can be used as FastAPI dependency
to easily retrieve the user object
"""

import typing

from fastapi import Request


async def get_user(request: Request) -> None or typing.Any:
    """
    This function can be used as FastAPI dependency
    to easily retrieve the user object
    """
    if "user" in request.scope:
        return request.scope["user"]

    return None
