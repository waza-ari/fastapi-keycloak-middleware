"""
This module contains a helper method that can be used to initialize the
middleware. It can also automatically add exception responses for 401
and 403 responses and modify the OpenAPI schema to correctly include
OpenID Connect information.
"""

import logging
import typing

from fastapi import Depends, FastAPI
from fastapi.security import OpenIdConnect

from fastapi_keycloak_middleware.middleware import KeycloakMiddleware
from fastapi_keycloak_middleware.schemas.exception_response import ExceptionResponse
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)

log = logging.getLogger(__name__)


def setup_keycloak_middleware(  # pylint: disable=too-many-arguments
    app: FastAPI,
    keycloak_configuration: KeycloakConfiguration,
    exclude_patterns: typing.List[str] | None = None,
    user_mapper: typing.Callable[[typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]]
    | None = None,
    scope_mapper: typing.Callable[[typing.List[str]], typing.Awaitable[typing.List[str]]]
    | None = None,
    add_exception_response: bool = True,
    add_swagger_auth: bool = False,
    swagger_openId_base_url: str | None = None,
    swagger_auth_scopes: typing.List[str] | None = None,
    swagger_auth_pkce: bool = True,
    swagger_scheme_name: str = "keycloak-openid",
):
    """
    This function can be used to initialize the middleware on an existing
    FastAPI application. Note that the middleware can also be added directly.

    This function adds the benefit of automatically adding correct response
    types as well as the OpenAPI configuration.

    :param app: The FastAPI app instance, required
    :param keycloak_configuration: KeyCloak configuration object. For potential
        options, see the KeycloakConfiguration schema.
    :type keycloak_configuration: KeycloakConfiguration
    :param exclude_patterns: List of paths that should be excluded from authentication.
        Defaults to an empty list. The strings will be compiled to regular expressions
        and used to match the path. If the path matches, the middleware
        will skip authentication.
    :type exclude_patterns: typing.List[str], optional
    :param user_mapper: Custom async function that gets the userinfo extracted from AT
        and should return a representation of the user that is meaningful to you,
        the user of this library, defaults to None
    :type user_mapper:
        typing.Callable[ [typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any] ]
        optional
    :param scope_mapper: Custom async function that transforms the claim values
        extracted from the token to permissions meaningful for your application,
        defaults to None
    :type scope_mapper: typing.Callable[[typing.List[str]], typing.List[str]], optional
    :param add_exception_response: Whether to add exception responses for 401 and 403.
        Defaults to True.
    :type add_exception_response: bool, optional
    :param add_swagger_auth: Whether to add OpenID Connect authentication to the OpenAPI
        schema. Defaults to False.
    :type add_swagger_auth: bool, optional
    :param swagger_openId_base_url: Base URL for the OpenID Connect configuration that will be used
        by the Swagger UI. This parameter allows you to specify a different base URL than
        the one in keycloak_configuration.url. This is particularly useful in Docker
        container scenarios where the internal and external URLs differ.

        For example, inside a Docker container network, Keycloak's OpenID configuration
        endpoint might be available at:
        http://host.docker.internal:8080/auth/realms/master/.well-known/openid-configuration

        However, external clients like Swagger UI cannot resolve host.docker.internal.
        In this case, you would set:
        - keycloak_configuration.url:
        -- "http://host.docker.internal:8080" (for internal communication)
        - swagger_openId_base_url:
        -- "http://localhost:8080" (for Swagger UI access)

        If not specified, defaults to using keycloak_configuration.url.
    :type swagger_openId_base_url: str, optional
    :param swagger_auth_scopes: Scopes to use for the Swagger UI authentication.
        Defaults to ['openid', 'profile'].
    :type swagger_auth_scopes: typing.List[str], optional
    :param swagger_auth_pkce: Whether to use PKCE with the Swagger UI authentication.
        Defaults to True.
    :type swagger_auth_pkce: bool, optional
    :param swagger_scheme_name: Name of the OpenAPI security scheme. Defaults to
        'keycloak-openid'.
    :type swagger_scheme_name: str, optional
    """

    # Add middleware
    app.add_middleware(
        KeycloakMiddleware,
        keycloak_configuration=keycloak_configuration,
        user_mapper=user_mapper,
        scope_mapper=scope_mapper,
        exclude_patterns=exclude_patterns,
    )

    # Add exception responses if requested
    if add_exception_response:
        router = app.router if isinstance(app, FastAPI) else app
        if 401 not in router.responses:
            log.debug("Adding 401 exception response")
            router.responses[401] = {
                "description": "Unauthorized",
                "model": ExceptionResponse,
            }
        else:
            log.warning(
                "Middleware is configured to add 401 exception response but it already exists"
            )

        if 403 not in router.responses:
            log.debug("Adding 403 exception response")
            router.responses[403] = {
                "description": "Forbidden",
                "model": ExceptionResponse,
            }
        else:
            log.warning(
                "Middleware is configured to add 403 exception response but it already exists"
            )
    else:
        log.debug("Skipping adding exception responses")

    # Add OpenAPI schema
    if add_swagger_auth:
        suffix = ".well-known/openid-configuration"
        openId_base_url = swagger_openId_base_url or keycloak_configuration.url
        security_scheme = OpenIdConnect(
            openIdConnectUrl=f"{openId_base_url}/realms/{keycloak_configuration.realm}/{suffix}",
            scheme_name=swagger_scheme_name,
            auto_error=False,
        )
        client_id = (
            keycloak_configuration.swagger_client_id
            if keycloak_configuration.swagger_client_id
            else keycloak_configuration.client_id
        )
        scopes = swagger_auth_scopes if swagger_auth_scopes else ["openid", "profile"]
        swagger_ui_init_oauth = {
            "clientId": client_id,
            "scopes": scopes,
            "appName": app.title,
            "usePkceWithAuthorizationCodeGrant": swagger_auth_pkce,
        }
        app.swagger_ui_init_oauth = swagger_ui_init_oauth
        app.router.dependencies.append(Depends(security_scheme))
