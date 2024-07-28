"""
This module providers a decorator that can be used to check if a user has a specific
permission.
"""

# pylint: disable=logging-not-lazy,consider-using-f-string
# NOTE: Using % formatting is the safest way as we allow custom loggers.
#       There could be custom loggers that handle arguments differently

import logging
import typing
from collections import OrderedDict
from collections.abc import Callable
from functools import wraps
from inspect import Parameter, signature
from warnings import warn

import starlette
from fastapi import HTTPException
from starlette.requests import Request

from fastapi_keycloak_middleware.decorators.strip_request import strip_request
from fastapi_keycloak_middleware.schemas.authorization_methods import (
    AuthorizationMethod,
)
from fastapi_keycloak_middleware.schemas.authorization_result import AuthorizationResult
from fastapi_keycloak_middleware.schemas.match_strategy import MatchStrategy

log = logging.getLogger(__name__)


def require_permission(
    permissions: typing.Union[str, typing.List[str]],
    match_strategy: MatchStrategy = MatchStrategy.AND,
) -> Callable:
    """
    This decorator can be used to enfore certain permissions for the path
    function it is applied to.

    :param permissions: The permissions that are required to access the path
        function. Can be a single string or a list of strings.
    :type permissions: typing.Union[str, typing.List[str]], optional
    :param match_strategy: The strategy that is used to match the permissions.
        Defaults to ``MatchStrategy.AND``.
    :type match_strategy: MatchStrategy, optional
    :return: The decorated function
    """

    warn(
        "The decorator method is deprecated and will be removed in the next major version. "
        "Please transition to dependency based permission checking.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Check if permissions is a single string, convert to list if so
    if isinstance(permissions, str):
        permissions = [permissions]

    # Check if match_strategy is valid
    if match_strategy not in MatchStrategy:
        raise ValueError(f"Invalid match strategy. Must be 'and' or 'or'. Got {match_strategy}")

    def _check_permission(
        requested_permission: typing.List[str], allowed_scopes: typing.List[str]
    ) -> typing.Tuple[bool, typing.List[str]]:
        """
        Check if the user has permission based on the matching strategy
        """
        # Get matching permissions
        matching_permissions = [
            permission for permission in requested_permission if permission in allowed_scopes
        ]

        if match_strategy == MatchStrategy.AND:
            return (
                set(requested_permission) == set(matching_permissions),
                matching_permissions,
            )
        return len(matching_permissions) > 0, matching_permissions

    def decorator(func):
        """
        Inner decorator
        """

        # Remove the request argument by applying the provided decorator. See
        # https://stackoverflow.com/questions/44548047/creating-decorator-out-of-another-decorator-python
        func = strip_request(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request", None)

            assert isinstance(request, Request)

            user = request.get("user", None)

            log.debug(f"Checking permission {permissions} for user {str(user)}")

            allowed_scopes = request.get("auth", [])

            # Check if user has permission
            allowed, matching_permissions = _check_permission(permissions, allowed_scopes)

            if allowed:
                log.info(f"Permission granted for user {str(user)}")
                log.debug(f"Matching permissions: {matching_permissions}")

                # Check if "matched_scopes" is in function signature.
                # If so, add it to the function call.
                if "authorization_result" in signature(func).parameters.keys():
                    kwargs["authorization_result"] = AuthorizationResult(
                        method=AuthorizationMethod.CLAIM,
                        authorized=True,
                        matched_scopes=matching_permissions,
                    )

                return await func(*args, **kwargs)

            log.warning(f"Permission {permissions} denied for user {str(user)}")
            raise HTTPException(status_code=403, detail="Permission denied")

        # Override signature
        # See https://peps.python.org/pep-0362/#signature-object
        # Note that the signature is immutable, so we need to create a new one
        sig = signature(func)
        parameters: OrderedDict = sig.parameters
        if "request" in parameters.keys():
            return wrapper

        parameters = [
            Parameter(
                name="request",
                kind=Parameter.POSITIONAL_OR_KEYWORD,
                default=Parameter.empty,
                annotation=starlette.requests.Request,
            ),
            *parameters.values(),
        ]
        new_sig = sig.replace(parameters=parameters, return_annotation=sig.return_annotation)
        wrapper.__signature__ = new_sig
        return wrapper

    return decorator
