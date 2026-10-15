"""
This module contains helpers to read claims from a decoded access token.
"""

import typing

_MISSING = object()


def get_claim(claims: typing.Mapping[str, typing.Any], path: str) -> typing.Any:
    """
    Returns the value of a claim. The path can either be a top level claim name
    or a dot separated path into nested objects, e.g. ``realm_access.roles``.

    A key that exists literally always wins over walking the path, so claim names
    that contain dots themselves (e.g. namespaced claims like
    ``https://example.com/roles`` or Keycloak client IDs in
    ``resource_access.<client>.roles``) are still found.

    :param claims: The decoded token claims
    :type claims: typing.Mapping[str, typing.Any]
    :param path: Claim name or dot separated path to the claim
    :type path: str
    :raises KeyError: If the claim does not exist
    :return: The claim value
    :rtype: typing.Any
    """
    parts = path.split(".")

    def _walk(node: typing.Any, start: int) -> typing.Any:
        if start == len(parts):
            return node
        if not isinstance(node, typing.Mapping):
            return _MISSING
        # Try the longest key first so that keys containing dots take precedence
        for end in range(len(parts), start, -1):
            key = ".".join(parts[start:end])
            if key in node:
                value = _walk(node[key], end)
                if value is not _MISSING:
                    return value
        return _MISSING

    value = _walk(claims, 0)
    if value is _MISSING:
        raise KeyError(path)
    return value


def normalize_scopes(value: typing.Any) -> typing.Any:
    """
    Normalizes the value of an authorization claim. Space delimited strings, as
    used by the OAuth 2.0 ``scope`` claim (RFC 6749, RFC 9068) or the Entra ID
    ``scp`` claim, are split into a list. Any other value is returned unchanged.

    :param value: The raw claim value
    :type value: typing.Any
    :return: The normalized value
    :rtype: typing.Any
    """
    if isinstance(value, str):
        return value.split()
    return value
