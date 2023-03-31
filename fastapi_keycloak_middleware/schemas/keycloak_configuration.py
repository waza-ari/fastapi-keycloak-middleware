"""
This module contains the schema to configure Keycloak.
"""

from pydantic import BaseModel, Field

from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)


class KeycloakConfiguration(BaseModel):  # pylint: disable=too-few-public-methods
    """
    This is a Pydantic schema used to pass backend konfiguration
    for the Keycloak Backend to the middleware.

    :param realm: Keycloak realm that should be used for token authentication.
    :type realm: str
    :param url: URL of the Keycloak server. If you use legacy Keycloak versions
        or still have the auth context, you need to add the auth context to the URL.
    :type url: str
    :param client_id: Client ID of the client used to validate the token. The client
        id is only needed if you use the introspection endpoint.
    :type client_id: str, optional
    :param client_secret: Client secret of the client used to validate the token.
        The client secret is only needed if you use the introspection endpoint.
    :type client_secret: str, optional
    :param claims: List of claims that should be extracted from the access token.
        Defaults to
        ``["sub", "name", "family_name", "given_name", "preferred_username", "email"]``.
    :type claims: list[str], optional
    :param reject_on_missing_claim: Whether to reject the request if a claim is missing.
        Defaults to ``True``.
    :type reject_on_missing_claim: bool, optional
    :param authentication_scheme: Authentication scheme to use. Defaults to ``Bearer``.
    :type authentication_scheme: str, optional
    :param authorization_method: Authorization method to use. Defaults to ``NONE``.
    :type authorization_method: AuthorizationMethod, optional
    :param authorization_claim: Claim to use for extracting authorization scopes.
        Defaults to ``roles``.
    :type authorization_claim: str, optional
    :param use_introspection_endpoint: Whether to use the introspection endpoint
        for token validation. Should not be needed for Keycloak in general
        as Keycloak doesn't support opaque tokens. Defaults to ``False``.
    :type use_introspection_endpoint: bool, optional
    :param enable_device_authentication: Whether to enable device authentication.
        If device authentication is enabled, the middleware will ignore required user
        claims and not attempt to map the user. The token will be validated and then the
        request forwarded unmodified. Defaults to ``False``.
    :type enable_device_authentication: bool, optional
    :param device_authentication_claim: This claim will be used to check if the token
        is a device token. Defaults to ``is_device``. This is only used if
        ``enable_device_authentication`` is set to ``True``. The value
        is extracted from the claim and checked if its a truthy value.
        To be specific, ``bool(value)`` must evaluate to ``True``.
    """

    realm: str = Field(..., title="Realm", description="The realm to use.")
    url: str = Field(..., title="URL", description="The URL of the Keycloak server.")
    client_id: str = Field(..., title="Client ID", description="The client ID.")
    client_secret: str = Field(
        ..., title="Client Secret", description="The client secret."
    )
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
    use_introspection_endpoint: bool = Field(
        False,
        title="Use Introspection Endpoint",
        description="Whether to use the introspection endpoint.",
    )
    enable_device_authentication: bool = Field(
        False,
        title="Enable Device Authentication",
        description="Whether to enable device authentication. If device authentication"
        " is enabled, the middleware will ignore required user claims and not attempt"
        " to map the user. The token will be validated and then the request"
        " forwarded unmodified.",
    )
    device_authentication_claim: str = Field(
        "is_device",
        title="Device Authentication Claim",
        description="The claim that will be checked. If present and if it evaluates to"
        " true, the device authentication will be applied for the request.",
    )
