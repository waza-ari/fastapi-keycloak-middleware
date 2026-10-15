"""
This module contains an Enum specifying the type of an authenticated principal.
"""

from enum import Enum


class PrincipalType(Enum):
    """
    The type of principal an access token was issued to.

    - ``PrincipalType.USER``: A human user, e.g. a token obtained using the
      authorization code flow.
    - ``PrincipalType.SERVICE``: A service acting on its own behalf, e.g. a token
      obtained using the client credentials grant.
    """

    USER = "user"
    SERVICE = "service"
