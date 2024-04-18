"""
This module contains the schema holding an authorization result

It is used by the FastAPI dependency to return the result of the authorization
for further processing by the API endpoint
"""

import typing

from pydantic import BaseModel, Field

from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)


class AuthorizationResult(BaseModel):  # pylint: disable=too-few-public-methods
    """
    This class contains the schema representing an authorization result.

    The following attributes will be set when returning the class in your
    path function:
    """

    #: The method that was used to authorize the user
    method: typing.Union[None, AuthorizationMethod] = Field(
        default=None,
        title="Method",
        description="The method used to authorize the user.",
    )
    #: Whether the user is authorized or not
    authorized: bool = Field(
        default=False,
        title="Authorized",
        description="Whether the user is authorized or not.",
    )
    #: The scopes that matched the user's scopes
    matched_scopes: typing.List[str] = Field(
        default=[],
        title="Matched Scopes",
        description="The scopes that matched the user's scopes.",
    )
