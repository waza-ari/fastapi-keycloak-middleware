"""
This module provides the middleware for the FastAPI framework.

It is inspired by the fastapi-auth-middleware package published
here: https://github.com/code-specialist/fastapi-auth-middleware
"""

import logging
import re
import typing

from jwcrypto.common import JWException
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi_keycloak_middleware.exceptions import (
    AuthHeaderMissing,
    AuthInvalidToken,
    AuthUserError,
)
from fastapi_keycloak_middleware.keycloak_backend import KeycloakBackend
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)

log = logging.getLogger(__name__)


class KeycloakMiddleware:
    """
    This class represents the middleware for FastAPI. It will authenticate
    a user based on a token. It currently only supports one backend
    (Keycloak backend).

    The middleware will add the user object to the request object. It
    optionally can also compile a list of scopes and add it to the request
    object as well, which can later be used for authorization.

    :param app: The FastAPI app instance, is automatically passed by FastAPI
    :type app: FastAPI
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
    :type scope_mapper:
        typing.Callable[[typing.List[str]], typing.Awaitable[typing.List[str]]], optional
    """

    def __init__(
        self,
        app: ASGIApp,
        keycloak_configuration: KeycloakConfiguration,
        exclude_patterns: typing.List[str] | None = None,
        user_mapper: typing.Callable[[typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]]
        | None = None,
        scope_mapper: typing.Callable[[typing.List[str]], typing.Awaitable[typing.List[str]]]
        | None = None,
    ):
        """Middleware constructor"""
        log.info("Initializing Keycloak Middleware")
        self.app = app
        self.backend: KeycloakBackend = KeycloakBackend(
            keycloak_configuration=keycloak_configuration,
            user_mapper=user_mapper,
        )
        self.scope_mapper = scope_mapper
        self.inspect_websockets = keycloak_configuration.enable_websocket_support
        log.debug("Keycloak Middleware initialized")

        # Try to compile patterns
        self.exclude_paths = []
        if exclude_patterns and isinstance(exclude_patterns, list):
            for path in exclude_patterns:
                try:
                    self.exclude_paths.append(re.compile(path))
                except re.error:
                    log.error("Could not compile regex for exclude pattern %s", path)

    async def _exclude_path(self, path: str) -> bool:
        """
        Checks if a path should be excluded from authentication

        :param path: The path to check
        :type path: str
        :return: True if the path should be excluded, False otherwise
        :rtype: bool
        """
        for pattern in self.exclude_paths:
            if pattern.match(path):
                return True
        return False

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        log.debug("Keycloak Middleware is handling request")

        supported_protocols = ["http"]
        if self.inspect_websockets:
            supported_protocols.append("websocket")

        if scope["type"] not in supported_protocols:  # Filter for relevant requests
            log.debug("Skipping non-HTTP request")
            await self.app(scope, receive, send)  # pragma nocover # Bypass
            return

        # Extract path from scope
        path = scope["path"]
        if await self._exclude_path(path):
            log.debug("Skipping authentication for excluded path %s", path)
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)  # Scoped connection

        try:  # to Authenticate
            # Run Backend authentication

            log.info("Trying to authenticate user")

            auth, user = await self.backend.authenticate(connection)

            log.debug("User has been authenticated successfully")

            # Map scope if needed
            if self.scope_mapper:
                log.debug("Calling user provided scope mapper")
                auth = await self.scope_mapper(auth)

            scope["auth"], scope["user"] = auth, user

        except AuthHeaderMissing:  # Request has no 'Authorization' HTTP Header
            response = JSONResponse(
                {"detail": "Your request is missing an 'Authorization' HTTP header"},
                status_code=401,
            )
            log.warning("Request is missing an 'Authorization' HTTP header")
            await response(scope, receive, send)
            return

        except AuthUserError:
            response = JSONResponse(
                {"detail": "Could not find a user based on this token"}, status_code=401
            )
            log.warning("Could not find a user based on the provided token")
            await response(scope, receive, send)
            return

        except AuthInvalidToken:
            response = JSONResponse(
                {"detail": "Unable to verify provided access token"}, status_code=401
            )
            log.warning("Provided access token could not be validated")
            await response(scope, receive, send)
            return

        except JWException as exc:
            response = JSONResponse(
                {"detail": f"Error while validating access token: {exc}"},
                status_code=401,
            )
            log.warning("An error occurred while validating the token")
            await response(scope, receive, send)
            return

        except Exception as exc:  # pylint: disable=broad-except
            response = JSONResponse(
                {"detail": f"An error occurred: {exc.__class__.__name__}"},
                status_code=401,
            )
            log.error("An error occurred while authenticating the user")
            log.exception(exc)
            await response(scope, receive, send)
            return

        log.debug("Sending request to next middleware")
        await self.app(scope, receive, send)  # Token is valid
