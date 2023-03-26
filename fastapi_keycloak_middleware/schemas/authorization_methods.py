"""
This module contains an Enum specifying the authorization methods.
"""

from enum import Enum


class AuthorizationMethod(Enum):
    """
    This Enum specifies the authorization methods.
    """

    NONE = 0
    CLAIM = 1
