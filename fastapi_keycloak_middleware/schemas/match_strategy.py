"""
This module contains an Enum specifying the match strategy used
by the CheckPermissions dependency
"""

from enum import Enum


class MatchStrategy(Enum):
    """
    This Enum can be used to set the authorization match strategy
    if multiple scopes are passed to the ``CheckPermissions`` dependency.
    Please use the Enum values instead of the values behind the Enums.

    Supported options are:

    - ``MatchStrategy.OR``: One of the provided scopes must match
    - ``MatchStrategy.AND``: All of the provided scopes must match
    """

    OR = "or"
    AND = "and"
