"""
This module contains a FastAPI dependency that can be used to validate that a user
has a certain permission before accessing a path
"""

import logging
import typing

from fastapi import Depends, HTTPException

from ..schemas.authorization_methods import AuthorizationMethod
from ..schemas.authorization_result import AuthorizationResult
from ..schemas.match_strategy import MatchStrategy
from .get_auth import get_auth
from .get_user import get_user

log = logging.getLogger(__name__)


class CheckPermissions:
    """
    This class can be used as FastAPI dependency to check if a user has
    the required permissions to access a path
    """

    def __init__(
        self,
        required_permission: typing.Union[str, typing.List[str]],
        match_strategy: MatchStrategy = MatchStrategy.AND,
    ):
        """
        Initialize the dependency. The required permission can be a single string
        or a list of strings. The match strategy can be either AND or OR, meaning
        that all permissions must be present or at least one permission must be present.

        :param required_permission: _description_
        :type required_permission: typing.Union[str, typing.List[str]]
        :param match_strategy: _description_, defaults to MatchStrategy.AND
        :type match_strategy: MatchStrategy, optional
        """

        # Check if permissions is a single string, convert to list if so
        if isinstance(required_permission, str):
            required_permission = [required_permission]

        self.required_permission: typing.List[str] = required_permission

        # Check if match_strategy is valid
        if match_strategy not in MatchStrategy:
            raise ValueError(f"Invalid match strategy. Must be 'and' or 'or'. Got {match_strategy}")

        self.match_strategy = match_strategy

    def __call__(self, user=Depends(get_user), auth: typing.List[str] = Depends(get_auth)):
        log.debug(f"Checking permission {self.required_permission} for user {str(user)}")

        # Get matching permissions
        matching_permissions = [
            permission for permission in self.required_permission if permission in auth
        ]

        # If match strategy is AND, all permissions must be present
        # If match strategy is OR, at least one permission must be present
        if (
            self.match_strategy == MatchStrategy.AND
            and set(self.required_permission) == set(matching_permissions)
        ) or (self.match_strategy == MatchStrategy.OR and len(matching_permissions) > 0):
            log.info(f"Permission granted for user {str(user)}")
            log.debug(f"Matching permissions: {matching_permissions}")
            return AuthorizationResult(
                authorized=True,
                matched_scopes=matching_permissions,
                method=AuthorizationMethod.CLAIM,
            )

        # No matching permissions found, raise an exception
        log.warning(f"Permission {self.required_permission} denied for user {str(user)}")
        raise HTTPException(status_code=403, detail="Permission denied")
