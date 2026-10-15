"""
This module contains a cache for the JSON Web Key Set (JWKS) of the realm.

The key set is fetched lazily on the first request and refreshed whenever a token
references a key ID that is not known yet, which happens after the realm signing
key has been rotated. Refreshes are rate limited, so tokens with arbitrary key
IDs cannot make the application hammer the identity provider.
"""

import asyncio
import json
import logging
import typing
from time import monotonic

from jwcrypto import jwk
from jwcrypto.common import JWException, base64url_decode
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakError

from fastapi_keycloak_middleware.exceptions import AuthKeycloakError

log = logging.getLogger(__name__)


def get_token_kid(token: str) -> str | None:
    """
    Returns the key ID from the (unverified) header of a JWT, or None if the token
    has no key ID or the header cannot be parsed.

    :param token: The encoded JWT
    :type token: str
    :return: The key ID
    :rtype: str | None
    """
    try:
        header = json.loads(base64url_decode(token.split(".", 1)[0]))
    except ValueError:
        return None
    if not isinstance(header, dict):
        return None
    kid = header.get("kid")
    return kid if isinstance(kid, str) else None


class KeySetCache:
    """
    Caches the signing keys of the realm as :class:`jwcrypto.jwk.JWKSet`.

    :param keycloak_openid: The client used to fetch the key set
    :type keycloak_openid: KeycloakOpenID
    :param refresh_interval: Minimum number of seconds between two fetches
    :type refresh_interval: float
    """

    def __init__(self, keycloak_openid: KeycloakOpenID, refresh_interval: float):
        self._keycloak_openid = keycloak_openid
        self._refresh_interval = refresh_interval
        self._key_set: jwk.JWKSet | None = None
        self._last_fetch: float | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _parse(certs: typing.Dict[str, typing.Any]) -> jwk.JWKSet:
        """
        Builds a key set from the JWKS response, keeping signing keys only.
        """
        key_set = jwk.JWKSet()
        for key in certs.get("keys", []):
            if key.get("use", "sig") != "sig":
                continue
            try:
                key_set.add(jwk.JWK(**key))
            except (JWException, TypeError, ValueError):
                log.warning("Skipping unsupported key %s from key set", key.get("kid"))
        return key_set

    def _is_known(self, kid: str | None) -> bool:
        if self._key_set is None:
            return False
        return kid is None or self._key_set.get_key(kid) is not None

    async def get_key_set(self, kid: str | None) -> jwk.JWKSet:
        """
        Returns the key set to validate a token with the given key ID.

        The key set is fetched if it has not been loaded yet or if the key ID is
        unknown, at most once per refresh interval. If the key ID is still unknown
        afterwards, the cached key set is returned and validation fails.

        :param kid: The key ID from the token header
        :type kid: str | None
        :raises AuthKeycloakError: If no key set could be loaded at all
        :return: The key set
        :rtype: jwk.JWKSet
        """
        if self._is_known(kid):
            return typing.cast(jwk.JWKSet, self._key_set)

        async with self._lock:
            # Another request may have refreshed the key set while waiting for the lock
            if not self._is_known(kid):
                await self._refresh(kid)

        if self._key_set is None:
            raise AuthKeycloakError("No key set available")
        return self._key_set

    async def _refresh(self, kid: str | None):
        """
        Fetches the key set, unless the last attempt is more recent than the refresh
        interval. Failed attempts count as well, so an unavailable Keycloak server is
        not contacted on every request.
        """
        now = monotonic()
        if self._last_fetch is not None and now - self._last_fetch < self._refresh_interval:
            log.debug("Not fetching key set for key ID %s, rate limit applies", kid)
            return

        self._last_fetch = now
        log.info("Fetching key set from Keycloak (requested key ID: %s)", kid)
        try:
            self._key_set = self._parse(await self._keycloak_openid.a_certs())
        except (KeycloakError, JWException, ValueError) as exc:
            # Keep the previous key set, tokens signed with known keys stay valid
            log.error("Failed to fetch key set from Keycloak: %s", exc)
