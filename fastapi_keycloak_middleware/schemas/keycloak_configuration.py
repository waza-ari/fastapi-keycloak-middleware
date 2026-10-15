"""
This module contains the schema to configure Keycloak.
"""

from typing import Union

from jwcrypto import jwk
from pydantic import BaseModel, ConfigDict, Field

from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)


class KeycloakConfiguration(BaseModel):  # pylint: disable=too-few-public-methods
    """
    This is a Pydantic schema used to pass backend configuration
    for the Keycloak Backend to the middleware.

    :param realm: Keycloak realm that should be used for token authentication.
    :type realm: str
    :param url: URL of the Keycloak server. If you use legacy Keycloak versions
        or still have the auth context, you need to add the auth context to the URL.
    :type url: str
    :param client_id: Client ID of the client used to validate the token.
    :type client_id: str
    :param swagger_client_id: Client ID for swagger UI authentication. Defaults to None.
    :type swagger_client_id: str, optional
    :param client_secret: Client secret of the client used to validate the token.
        The client secret is only needed if you use the introspection endpoint.
    :type client_secret: str, optional
    :param required_claims: Claims that must be present in every access token, otherwise
        the request is rejected. Nested claims can be referenced with a dot separated
        path. The user and service mappers always receive all claims of the token.
        Defaults to ``["sub"]``.
    :type required_claims: list[str], optional
    :param authentication_scheme: Authentication scheme to use. Defaults to ``Bearer``.
    :type authentication_scheme: str, optional
    :param authorization_method: Authorization method to use. Defaults to ``NONE``.
    :type authorization_method: AuthorizationMethod, optional
    :param authorization_claim: Claim to use for extracting authorization scopes.
        Nested claims can be referenced with a dot separated path, e.g.
        ``realm_access.roles``. Space delimited string values (like the OAuth 2.0
        ``scope`` claim) are split into a list. Defaults to ``roles``.
    :type authorization_claim: str, optional
    :param use_introspection_endpoint: Whether to use the introspection endpoint
        for token validation. Should not be needed for Keycloak in general
        as Keycloak doesn't support opaque tokens. Defaults to ``False``.
    :type use_introspection_endpoint: bool, optional
    :param verify: Whether to verify SSL connection. Defaults to ``True``
    :type verify: Union[bool,str], optional
    :param validate_token: Whether to validate the token. Defaults to ``True``.
    :type validate_token: bool, optional
    :param validation_options: Decode options that are passed to `JWCrypto`'s JWT
        constructor. Defaults to ``{}``. See the following project for an overview of
        acceptable options: https://jwcrypto.readthedocs.io/en/latest/jwt.html
    :type validation_options: dict[str, Union[str, dict[str, Union[None, str]], list[str]]],
        optional
    :param enable_websocket_support: Whether to enable WebSocket support. Defaults to ``True``.
    :type enable_websocket_support: bool, optional
    :param websocket_cookie_name: Name of the cookie that contains the access token.
        Defaults to ``access_token``.
    :type websocket_cookie_name: str, optional
    """

    # Unknown options are rejected, so options removed in a major release are not
    # silently ignored
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    realm: str = Field(title="Realm", description="The realm to use.")
    url: str = Field(title="URL", description="The URL of the Keycloak server.")
    client_id: str = Field(title="Client ID", description="The client ID.")
    swagger_client_id: str | None = Field(
        default=None, title="Swagger Client ID", description="The client ID for the swagger UI."
    )
    client_secret: str | None = Field(
        default=None, title="Client Secret", description="The client secret."
    )
    required_claims: list[str] = Field(
        default=["sub"],
        title="Required Claims",
        description="Claims that must be present in every access token.",
    )
    authentication_scheme: str = Field(
        default="Bearer",
        title="Authentication Scheme",
        description="The authentication scheme to use.",
    )
    authorization_method: AuthorizationMethod = Field(
        default=AuthorizationMethod.NONE,
        title="Authorization Method",
        description="The authorization method to use.",
    )
    authorization_claim: str = Field(
        default="roles",
        title="Authorization Claim",
        description="The claim to use for authorization.",
    )
    use_introspection_endpoint: bool = Field(
        default=False,
        title="Use Introspection Endpoint",
        description="Whether to use the introspection endpoint.",
    )
    verify: Union[bool, str] = Field(
        default=True,
        title="Verify",
        description="Whether to verify the SSL connection",
    )
    validate_token: bool = Field(
        default=True,
        title="Validate Token",
        description="Whether to validate the token.",
    )
    validation_options: dict[
        str, Union[str, dict[str, Union[None, str]], list[str], jwk.JWK, jwk.JWKSet]
    ] = Field(
        default={},
        title="JWCrypto JWT Options",
        description="Decode options that are passed to jwcrypto's JWT constructor.",
    )
    enable_websocket_support: bool = Field(
        default=True,
        title="Enable WebSocket Support",
        description="if enabled, websocket connections are also checked for valid tokens.",
    )
    websocket_cookie_name: str = Field(
        default="access_token",
        title="WebSocket Cookie Name",
        description="The name of the cookie that contains the access token.",
    )
