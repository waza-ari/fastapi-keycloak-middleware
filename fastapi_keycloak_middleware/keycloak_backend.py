"""
This module contains the Keycloak backend.

It is used by the middleware to perform the actual authentication.
"""

import logging
import typing

import keycloak
from jwcrypto import jwk
from keycloak import KeycloakOpenID
from starlette.requests import HTTPConnection

from fastapi_keycloak_middleware.claims import get_claim, normalize_scopes
from fastapi_keycloak_middleware.exceptions import (
    AuthClaimMissing,
    AuthHeaderMissing,
    AuthInvalidToken,
    AuthKeycloakError,
    AuthServiceError,
    AuthUserError,
)
from fastapi_keycloak_middleware.fast_api_user import FastApiUser
from fastapi_keycloak_middleware.schemas.auth_context import AuthContext
from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)
from fastapi_keycloak_middleware.schemas.keycloak_configuration import (
    KeycloakConfiguration,
)
from fastapi_keycloak_middleware.schemas.principal_type import PrincipalType
from fastapi_keycloak_middleware.service_principal import ServicePrincipal

log = logging.getLogger(__name__)

#: Async function mapping the token claims to a user or service object
PrincipalMapper = typing.Callable[[typing.Dict[str, typing.Any]], typing.Awaitable[typing.Any]]
#: Function deciding whether the token claims belong to a service principal
ServiceDetector = typing.Callable[[typing.Dict[str, typing.Any]], bool]


class KeycloakBackend:
    """
    Backend to perform authentication using Keycloak
    """

    def __init__(
        self,
        keycloak_configuration: KeycloakConfiguration,
        user_mapper: PrincipalMapper | None = None,
        service_mapper: PrincipalMapper | None = None,
        service_detector: ServiceDetector | None = None,
    ):
        self.keycloak_configuration = keycloak_configuration
        self.keycloak_openid = self._get_keycloak_openid()
        if not self.keycloak_configuration.use_introspection_endpoint:
            self.public_key = self._get_public_key()
        self.user_mapper = user_mapper or KeycloakBackend._default_user_mapper
        self.service_mapper = service_mapper or KeycloakBackend._default_service_mapper
        self.service_detector = service_detector

    def _get_keycloak_openid(self) -> KeycloakOpenID:
        """
        Instance-scoped KeycloakOpenID object
        """
        return KeycloakOpenID(
            server_url=self.keycloak_configuration.url,
            client_id=self.keycloak_configuration.client_id,
            realm_name=self.keycloak_configuration.realm,
            client_secret_key=self.keycloak_configuration.client_secret,
            verify=self.keycloak_configuration.verify,
        )

    def _get_public_key(self) -> jwk.JWK:
        """
        Returns the public key used to validate tokens.
        This is only used if the introspection endpoint is not used.
        """
        log.debug("Fetching public key from Keycloak server at %s", self.keycloak_configuration.url)
        try:
            key = (
                "-----BEGIN PUBLIC KEY-----\n"
                + self.keycloak_openid.public_key()
                + "\n-----END PUBLIC KEY-----"
            )
            return jwk.JWK.from_pem(key.encode("utf-8"))
        except keycloak.exceptions.KeycloakGetError as exc:
            log.error("Failed to fetch public key from Keycloak server: %s", exc.error_message)
            raise AuthKeycloakError from exc

    @staticmethod
    async def _default_user_mapper(claims: typing.Dict[str, typing.Any]) -> FastApiUser:
        """
        Default user mapper, returns a FastApiUser built from the standard claims.
        """
        return FastApiUser(
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
            user_id=claims.get("sub", ""),
        )

    @staticmethod
    async def _default_service_mapper(claims: typing.Dict[str, typing.Any]) -> ServicePrincipal:
        """
        Default service mapper, returns a ServicePrincipal identified by the client ID.
        """
        return ServicePrincipal(
            client_id=claims.get("client_id") or claims.get("azp") or claims.get("sub", "")
        )

    def _get_token(self, conn: HTTPConnection) -> str:
        """
        Extracts the access token from the request.
        """
        # Websockets can't send custom headers from browsers, the token is read from a cookie
        if (
            self.keycloak_configuration.enable_websocket_support
            and conn.scope["type"] == "websocket"
        ):
            auth_header = conn.cookies.get(self.keycloak_configuration.websocket_cookie_name, None)
        else:
            auth_header = conn.headers.get("Authorization", None)

        if not auth_header:
            raise AuthHeaderMissing

        # Check if token starts with the authentication scheme
        token = auth_header.split(" ")
        if len(token) != 2 or token[0] != self.keycloak_configuration.authentication_scheme:
            raise AuthInvalidToken
        return token[1]

    async def _validate_token(self, token: str) -> typing.Dict[str, typing.Any]:
        """
        Validates the token and returns its claims.
        """
        # Depending on the chosen method by the user, either
        # use the introspection endpoint or decode the token
        if self.keycloak_configuration.use_introspection_endpoint:
            log.debug("Using introspection endpoint to validate token")
            try:
                token_info = await self.keycloak_openid.a_introspect(token)
            except keycloak.exceptions.KeycloakError as exc:
                raise AuthKeycloakError from exc
            # Expired, revoked or otherwise invalid tokens are reported as inactive
            if not token_info.get("active", False):
                raise AuthInvalidToken
            return token_info

        log.debug("Using keycloak public key to validate token")
        return await self.keycloak_openid.a_decode_token(
            token,
            self.keycloak_configuration.validate_token,
            **self.keycloak_configuration.validation_options,
            key=self.public_key,
        )

    def _get_scopes(self, claims: typing.Dict[str, typing.Any]) -> typing.List[str]:
        """
        Extracts the authorization scopes from the token claims.
        """
        if self.keycloak_configuration.authorization_method != AuthorizationMethod.CLAIM:
            return []

        claim = self.keycloak_configuration.authorization_claim
        try:
            scopes = normalize_scopes(get_claim(claims, claim))
        except KeyError as exc:
            log.warning("Authorization claim %s is missing in the token", claim)
            raise AuthClaimMissing(claim) from exc

        if not isinstance(scopes, list):
            log.warning("Authorization claim %s is neither a list nor a string", claim)
            raise AuthInvalidToken
        return scopes

    async def authenticate(self, conn: HTTPConnection) -> typing.Tuple[AuthContext, typing.Any]:
        """
        The authenticate method is invoked each time a route is called that
        the middleware is applied to.

        :return: The authentication context (with unmapped scopes) and the principal
            returned by the user or service mapper
        """
        claims = await self._validate_token(self._get_token(conn))

        for claim in self.keycloak_configuration.required_claims:
            try:
                get_claim(claims, claim)
            except KeyError as exc:
                log.warning("Required claim %s is missing in the token", claim)
                raise AuthClaimMissing(claim) from exc

        principal_type = PrincipalType.USER
        if self.service_detector and self.service_detector(claims):
            principal_type = PrincipalType.SERVICE
        log.debug("Token was issued to a principal of type %s", principal_type.value)

        scopes = self._get_scopes(claims)

        if principal_type == PrincipalType.SERVICE:
            mapper, error = self.service_mapper, AuthServiceError
        else:
            mapper, error = self.user_mapper, AuthUserError

        try:
            principal = await mapper(claims)
        except Exception as exc:
            log.warning("The %s mapper raised an exception: %s", principal_type.value, exc)
            raise error from exc

        if principal is None:
            log.warning("The %s mapper returned None, rejecting request", principal_type.value)
            raise error

        return AuthContext(principal_type=principal_type, claims=claims, scopes=scopes), principal
