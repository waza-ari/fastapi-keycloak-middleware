"""
This module provides the middleware for the FastAPI framework.

It is inspired by the fastapi-auth-middleware package published
here: https://github.com/code-specialist/fastapi-auth-middleware
"""
import logging
import typing

from fastapi import FastAPI
from starlette.requests import HTTPConnection
from starlette.responses import PlainTextResponse
from starlette.types import Receive, Scope, Send

from fastapi_keycloak_middleware.exceptions import (
    AuthHeaderMissing,
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
    Middleware for FastAPI that authenticates a user using a Keycloak access token.
    """

    def __init__(
        self,
        app: FastAPI,
        keycloak_configuration: KeycloakConfiguration,
        user_mapper: typing.Callable[
            [typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]
        ] = None,
        scope_mapper: typing.Callable[[typing.List[str]], typing.List[str]] = None,
    ):
        """
        Middleware for FastAPI that authenticates a user using a JWT token.
        """
        log.info("Initializing Keycloak Middleware")
        self.app = app
        self.backend: KeycloakBackend = KeycloakBackend(
            keycloak_configuration=keycloak_configuration,
            user_mapper=user_mapper,
        )
        self.scope_mapper = scope_mapper
        log.debug("Keycloak Middleware initialized")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        log.debug("Keycloak Middleware is handling request")

        if scope["type"] not in [
            "http",
            "websocket",
        ]:  # pragma nocover # Filter for relevant requests
            log.debug("Skipping non-HTTP request")
            await self.app(scope, receive, send)  # pragma nocover # Bypass
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

            log.debug("Sending request to next middleware")
            await self.app(scope, receive, send)  # Token is valid

        except AuthHeaderMissing:  # Request has no 'Authorization' HTTP Header
            response = self.auth_header_missing()
            log.warning("Request is missing an 'Authorization' HTTP header")
            await response(scope, receive, send)
            return

        except AuthTokenExpired:  # Token has expired
            response = self.token_has_expired()
            log.warning("Provided token has expired")
            await response(scope, receive, send)
            return

        except AuthUserError:
            response = self.user_not_found()
            log.warning("Could not find a user based on the provided token")
            await response(scope, receive, send)
            return

        except Exception as exc:  # pylint: disable=broad-except
            response = PlainTextResponse(f"An error occurred: {exc}", status_code=500)
            log.error("An error occurred while authenticating the user")
            await response(scope, receive, send)
            return

    @staticmethod
    def auth_header_missing(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the request
        is missing an 'Authorization' HTTP header.
        """
        return PlainTextResponse(
            "Your request is missing an 'Authorization' HTTP header", status_code=401
        )

    @staticmethod
    def token_has_expired(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the token has expired.
        """
        return PlainTextResponse("Your 'Authorization' HTTP header is invalid", status_code=401)

    @staticmethod
    def user_not_found(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the user was not found.
        """
        return PlainTextResponse("Could not find a user based on this token", status_code=401)
