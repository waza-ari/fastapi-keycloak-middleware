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
    """

    method: typing.Union[None, AuthorizationMethod] = Field(
        None,
        title="Method",
        description="The method used to authorize the user.",
    )
    authorized: bool = Field(
        False,
        title="Authorized",
        description="Whether the user is authorized or not.",
    )
    matched_scopes: typing.List[str] = Field(
        [],
        title="Matched Scopes",
        description="The scopes that matched the user's scopes.",
    )
