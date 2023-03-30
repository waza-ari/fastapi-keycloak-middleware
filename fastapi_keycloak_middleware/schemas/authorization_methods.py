"""
This module contains an Enum specifying the authorization methods.
"""

from enum import Enum


class AuthorizationMethod(Enum):
    """
    This Enum can be used to set authorization methods. Please use the Enum values
    instead of the values behind the Enums.

    Supported options are:

    - ``AuthorizationMethod.NONE``: No authorization is performed.
    - ``AuthorizationMethod.CLAIM``: Authorization is performed by extracting
      the authorization scopes from a claim.
    """

    NONE = 0
    CLAIM = 1
