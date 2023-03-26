"""
This module contains an Enum specifying the match strategy used
by the require_permission decorator
"""

from enum import Enum


class MatchStrategy(Enum):
    """
    This Enum specifies the authorization match strategy.
    """

    OR = "or"
    AND = "and"
