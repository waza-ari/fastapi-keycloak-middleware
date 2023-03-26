"""
This module contains the schema to configure Keycloak.
"""

from pydantic import BaseModel, Field

from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)


class KeycloakConfiguration(BaseModel):  # pylint: disable=too-few-public-methods
    """
    This class contains the schema to configure Keycloak.
    """

    realm: str = Field(..., title="Realm", description="The realm to use.")
    url: str = Field(..., title="URL", description="The URL of the Keycloak server.")
    client_id: str = Field(..., title="Client ID", description="The client ID.")
    client_secret: str = Field(..., title="Client Secret", description="The client secret.")
    claims: list[str] = Field(
        [
            "sub",
            "name",
            "family_name",
            "given_name",
            "preferred_username",
            "email",
        ],
        title="Claims",
        description="The claims to add to the user object.",
    )
    reject_on_missing_claim: bool = Field(
        True,
        title="Reject on Missing Claim",
        description="Whether to reject the request if a claim is missing.",
    )
    authentication_scheme: str = Field(
        "Bearer",
        title="Authentication Scheme",
        description="The authentication scheme to use.",
    )
    authorization_method: AuthorizationMethod = Field(
        AuthorizationMethod.NONE,
        title="Authorization Method",
        description="The authorization method to use.",
    )
    authorization_claim: str = Field(
        "roles",
        title="Authorization Claim",
        description="The claim to use for authorization.",
    )
