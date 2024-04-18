"""
This module contains a helper method that can be used to initialize the
middleware. It can also automatically add exception responses for 401
and 403 responses and modify the OpenAPI schema to correctly include
OpenID Connect information.
"""

import logging
import typing

from fastapi import FastAPI

from fastapi_keycloak_middleware.middleware import KeycloakMiddleware
from fastapi_keycloak_middleware.schemas.exception_response import ExceptionResponse
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)

log = logging.getLogger(__name__)


def setup_keycloak_middleware(
    app: FastAPI,
    keycloak_configuration: KeycloakConfiguration,
    exclude_patterns: typing.List[str] = None,
    user_mapper: typing.Callable[
        [typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]
    ] = None,
    scope_mapper: typing.Callable[[typing.List[str]], typing.List[str]] = None,
    add_exception_response: bool = True,
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
                "Middleware is configured to add 401 exception"
                " response but it already exists"
            )

        if 403 not in router.responses:
            log.debug("Adding 403 exception response")
            router.responses[403] = {
                "description": "Forbidden",
                "model": ExceptionResponse,
            }
        else:
            log.warning(
                "Middleware is configured to add 403 exception"
                " response but it already exists"
            )
    else:
        log.debug("Skipping adding exception responses")
