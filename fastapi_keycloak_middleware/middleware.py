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


class KeycloakMiddleware:  # pylint: disable=too-few-public-methods
    """
    This class represents the middleware for FastAPI. It will authenticate
    a user based on a token. It currently only supports one backend
    (Keycloak backend).

    The middleware will add the user object to the request object. It
    optionally can also compile a list of scopes and add it to the request
    object as well, which can later be used for authoirzation.

    :param app: The FastAPI app instance, is automatically passed by FastAPI
    :type app: FastAPI
    :param keycloak_configuration: KeyCloak configuration object. For potential
        options, see the KeycloakConfiguration schema.
    :type keycloak_configuration: KeycloakConfiguration
    :param user_mapper: Custom async function that gets the userinfo extracted from AT
        and should return a representation of the user that is meaningful to you,
        the user of this library, defaults to None
    :type user_mapper:
        typing.Callable[ [typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any] ], optional
    :param scope_mapper: Custom async function that transforms the claim values extracted
        from the token to permissions meaningful for your application, defaults to None
    :type scope_mapper: typing.Callable[[typing.List[str]], typing.List[str]], optional
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
        """Middleware constructor"""
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

        except Exception as exc:  # pylint: disable=broad-except
            response = PlainTextResponse(f"An error occurred: {exc}", status_code=500)
            log.error("An error occurred while authenticating the user")
            await response(scope, receive, send)
            return

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
        return PlainTextResponse("Your 'Authorization' HTTP header is invalid", status_code=401)

    @staticmethod
    def _user_not_found(*args, **kwargs):  # pylint: disable=unused-argument
        """
        Returns a response notifying the user that the user was not found.
        """
        return PlainTextResponse("Could not find a user based on this token", status_code=401)
