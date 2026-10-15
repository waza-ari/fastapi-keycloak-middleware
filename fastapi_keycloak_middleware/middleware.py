"""
This module provides the middleware for the FastAPI framework.

It is inspired by the fastapi-auth-middleware package published
here: https://github.com/code-specialist/fastapi-auth-middleware
"""

import dataclasses
import logging
import typing

from jwcrypto.common import JWException
from starlette.authentication import AuthCredentials
from starlette.requests import HTTPConnection
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from fastapi_keycloak_middleware.exceptions import (
    AuthClaimMissing,
    AuthHeaderMissing,
    AuthInvalidToken,
    AuthKeycloakError,
    AuthServiceError,
    AuthUserError,
)
from fastapi_keycloak_middleware.keycloak_backend import (
    KeycloakBackend,
    PrincipalMapper,
    ServiceDetector,
)
from fastapi_keycloak_middleware.schemas.exclude_rule import ExcludeRule
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)

log = logging.getLogger(__name__)

#: Async function mapping the scopes extracted from the token to application permissions
ScopeMapper = typing.Callable[[typing.List[str]], typing.Awaitable[typing.List[str]]]


class KeycloakMiddleware:
    """
    This class represents the middleware for FastAPI. It will authenticate
    a user or service based on a token. It currently only supports one backend
    (Keycloak backend).

    On success, the middleware adds the following keys to the request scope:

    - ``user``: The principal returned by the user or service mapper
    - ``auth``: A :class:`starlette.authentication.AuthCredentials` instance holding
      the authorization scopes
    - ``auth_context``: An :class:`AuthContext` with the principal type, all token
      claims and the authorization scopes

    :param app: The FastAPI app instance, is automatically passed by FastAPI
    :type app: FastAPI
    :param keycloak_configuration: KeyCloak configuration object. For potential
        options, see the KeycloakConfiguration schema.
    :type keycloak_configuration: KeycloakConfiguration
    :param exclude_patterns: Requests that should be excluded from authentication.
        Each entry is either an :class:`ExcludeRule`, or a string holding a regular
        expression that must match the **entire** request path. Defaults to an
        empty list. Invalid entries raise a ``ValueError``.
    :type exclude_patterns: typing.List[typing.Union[str, ExcludeRule]], optional
    :param user_mapper: Custom async function that receives the claims of a user token
        and returns a representation of the user that is meaningful to your application.
        Returning ``None`` rejects the request. Defaults to returning a ``FastApiUser``.
    :type user_mapper:
        typing.Callable[[typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]], optional
    :param service_mapper: Custom async function that receives the claims of a service
        token and returns a representation of the service that is meaningful to your
        application. Returning ``None`` rejects the request. Defaults to returning a
        ``ServicePrincipal``.
    :type service_mapper:
        typing.Callable[[typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]], optional
    :param service_detector: Function that receives the token claims and returns whether
        the token was issued to a service instead of a user. If not set, every token is
        treated as a user token.
    :type service_detector: typing.Callable[[typing.Dict[str, typing.Any]], bool], optional
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
        exclude_patterns: typing.Sequence[typing.Union[str, ExcludeRule]] | None = None,
        user_mapper: PrincipalMapper | None = None,
        service_mapper: PrincipalMapper | None = None,
        service_detector: ServiceDetector | None = None,
        scope_mapper: ScopeMapper | None = None,
    ):
        """Middleware constructor"""
        log.info("Initializing Keycloak Middleware")
        self.app = app
        self.backend: KeycloakBackend = KeycloakBackend(
            keycloak_configuration=keycloak_configuration,
            user_mapper=user_mapper,
            service_mapper=service_mapper,
            service_detector=service_detector,
        )
        self.scope_mapper = scope_mapper
        self.inspect_websockets = keycloak_configuration.enable_websocket_support
        self.authentication_scheme = keycloak_configuration.authentication_scheme
        log.debug("Keycloak Middleware initialized")

        # Strings are full match path patterns, invalid entries raise a ValueError
        self.exclude_rules: typing.List[ExcludeRule] = [
            rule if isinstance(rule, ExcludeRule) else ExcludeRule(path=rule)
            for rule in exclude_patterns or []
        ]

    def _is_excluded(self, scope: Scope) -> bool:
        """
        Checks if a request should be excluded from authentication

        :param scope: The ASGI scope of the request
        :type scope: Scope
        :return: True if the request should be excluded, False otherwise
        :rtype: bool
        """
        return any(rule.matches(scope) for rule in self.exclude_rules)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        log.debug("Keycloak Middleware is handling request")

        supported_protocols = ["http"]
        if self.inspect_websockets:
            supported_protocols.append("websocket")

        if scope["type"] not in supported_protocols:  # Filter for relevant requests
            log.debug("Skipping non-HTTP request")
            await self.app(scope, receive, send)  # pragma nocover # Bypass
            return

        if self._is_excluded(scope):
            log.debug(
                "Skipping authentication for excluded request %s %s",
                scope.get("method", scope["type"]),
                scope["path"],
            )
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)  # Scoped connection

        try:  # to Authenticate
            # Run Backend authentication

            log.info("Trying to authenticate request")

            auth_context, principal = await self.backend.authenticate(connection)

            log.debug("Request has been authenticated successfully")

            # Map scope if needed
            if self.scope_mapper:
                log.debug("Calling user provided scope mapper")
                auth_context = dataclasses.replace(
                    auth_context, scopes=await self.scope_mapper(auth_context.scopes)
                )

            scope["user"] = principal
            scope["auth"] = AuthCredentials(auth_context.scopes)
            scope["auth_context"] = auth_context

        except AuthHeaderMissing:  # Request has no 'Authorization' HTTP Header
            log.warning("Request is missing an 'Authorization' HTTP header")
            # As per RFC 6750, no error code is included if no credentials were sent
            response = self._unauthorized(
                "Your request is missing an 'Authorization' HTTP header", error=None
            )

        except AuthUserError:
            log.warning("Could not find a user based on the provided token")
            response = self._unauthorized("Could not find a user based on this token")

        except AuthServiceError:
            log.warning("Could not find a service based on the provided token")
            response = self._unauthorized("Could not find a service based on this token")

        except AuthInvalidToken:
            log.warning("Provided access token could not be validated")
            response = self._unauthorized("Unable to verify provided access token")

        except AuthClaimMissing as exc:
            log.warning("Provided access token is missing a required claim")
            response = self._unauthorized(f"The access token is missing the claim '{exc}'")

        except AuthKeycloakError:
            log.error("Unable to reach Keycloak to validate the token")
            response = JSONResponse(
                {"detail": "Unable to reach the identity provider"}, status_code=503
            )

        except JWException as exc:
            log.warning("An error occurred while validating the token")
            response = self._unauthorized(f"Error while validating access token: {exc}")

        except Exception as exc:  # pylint: disable=broad-except
            log.error("An error occurred while authenticating the request")
            log.exception(exc)
            response = self._unauthorized(f"An error occurred: {exc.__class__.__name__}")

        else:
            log.debug("Sending request to next middleware")
            await self.app(scope, receive, send)  # Token is valid
            return

        await response(scope, receive, send)

    def _unauthorized(self, detail: str, error: str | None = "invalid_token") -> JSONResponse:
        """
        Builds a 401 response including the ``WWW-Authenticate`` challenge (RFC 6750)

        :param detail: Message returned in the response body
        :type detail: str
        :param error: Error code added to the challenge, defaults to ``invalid_token``
        :type error: str | None, optional
        :return: The response
        :rtype: JSONResponse
        """
        challenge = self.authentication_scheme
        if error:
            challenge += f' error="{error}"'
        return JSONResponse(
            {"detail": detail}, status_code=401, headers={"WWW-Authenticate": challenge}
        )
