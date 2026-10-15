"""
This module contains exceptions used by the middleware.
"""


class AuthHeaderMissing(Exception):
    """
    Raised when the Authorization header is missing.
    """


class AuthInvalidToken(Exception):
    """
    Raised when the token is invalid or malformed.
    """


class AuthKeycloakError(Exception):
    """
    Raised when there was a problem communicating with Keycloak
    """


class AuthClaimMissing(Exception):
    """
    Raised when one of the expected claims is missing.
    """


class AuthUserError(Exception):
    """
    Raised when the user mapper did not return a user object
    """


class AuthServiceError(Exception):
    """
    Raised when the service mapper did not return a service object
    """
