"""
This module contains the authentication context stored for each authenticated request.
"""

import typing
from dataclasses import dataclass, field

from fastapi_keycloak_middleware.schemas.principal_type import PrincipalType


@dataclass(frozen=True)
class AuthContext:
    """
    Result of a successful authentication. The middleware stores it in the
    ``auth_context`` key of the request scope, use the ``get_auth_context``
    dependency to retrieve it.
    """

    #: Whether the token was issued to a user or a service
    principal_type: PrincipalType
    #: All claims of the validated access token
    claims: typing.Dict[str, typing.Any] = field(default_factory=dict)
    #: The authorization scopes after applying the scope mapper. Empty if
    #: authorization is disabled.
    scopes: typing.List[str] = field(default_factory=list)
