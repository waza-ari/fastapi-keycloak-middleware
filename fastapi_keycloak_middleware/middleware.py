"""
This module provides the middleware for the FastAPI framework.

It is inspired by the fastapi-auth-middleware package published
here: https://github.com/code-specialist/fastapi-auth-middleware
"""
import logging
import re
import typing

from fastapi import FastAPI
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse
from starlette.types import Receive, Scope, Send

from fastapi_keycloak_middleware.exceptions import (
    AuthHeaderMissing,
    AuthInvalidToken,
    AuthTokenExpired,
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
    :param exclude_paths: List of paths that should be excluded from authentication.
        Defaults to an empty list. The strings will be compiled to regular expressions
        and used to match the path. If the path matches, the middleware
        will skip authentication.
    :type exclude_paths: typing.List[str], optional
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

    def __init__(
        self,
        app: FastAPI,
        keycloak_configuration: KeycloakConfiguration,
        exclude_patterns: typing.List[str] = None,
        user_mapper: typing.Callable[
            [typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]
        ] = None,
        scope_mapper: typing.Callable[[typing.List[str]], typing.List[str]] = None,
    ):
        """Middleware constructor"""
        log.info("Initializing Keycloak Middleware")
        self.app = app
        self.backend: KeycloakBackend = KeycloakBackend(
            keycloak_configuration=keycloak_configuration,
            user_mapper=user_mapper,
        )
        self.scope_mapper = scope_mapper
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

        if scope["type"] not in [
            "http",
            "websocket",
        ]:  # pragma nocover # Filter for relevant requests
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
            response = self._auth_header_missing()
            log.warning("Request is missing an 'Authorization' HTTP header")
            await response(scope, receive, send)
            return

        except AuthTokenExpired:  # Token has expired
            response = self._token_has_expired()
            log.warning("Provided token has expired")
            await response(scope, receive, send)
            return

        except AuthUserError:
            response = self._user_not_found()
            log.warning("Could not find a user based on the provided token")
            await response(scope, receive, send)
            return

        except AuthInvalidToken:
            response = self._invalid_token()
            log.warning("Provided access token could not be validated")
            await response(scope, receive, send)
            return

        except Exception as exc:  # pylint: disable=broad-except
            response = PlainTextResponse(
                f"An error occurred: {exc.__class__.__name__}", status_code=401
            )
            log.error("An error occurred while authenticating the user")
            await response(scope, receive, send)
            return

        log.debug("Sending request to next middleware")
        await self.app(scope, receive, send)  # Token is valid

    @staticmethod
    def _auth_header_missing(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the request
        is missing an 'Authorization' HTTP header.
        """
        return PlainTextResponse(
            "Your request is missing an 'Authorization' HTTP header", status_code=401
        )

    @staticmethod
    def _token_has_expired(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the token has expired.
        """
        return PlainTextResponse(
            "Your 'Authorization' HTTP header is invalid", status_code=401
        )

    @staticmethod
    def _user_not_found(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the user was not found.
        """
        return PlainTextResponse(
            "Could not find a user based on this token", status_code=401
        )

    @staticmethod
    def _invalid_token(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the acess token is invalid.
        """
        return PlainTextResponse(
            "Unable to verify provided access token", status_code=401
        )
