"""
This module contains a base user implementation

It is mainly used if the user does not provide a custom function to retrieve
the user based on the token claims
"""

import typing

from starlette.authentication import BaseUser


class FastApiUser(BaseUser):
    """Sample API User that gives basic functionality"""

    def __init__(self, first_name: str, last_name: str, user_id: typing.Any):
        """
        FastAPIUser Constructor
        """
        self.first_name = first_name
        self.last_name = last_name
        self.user_id = user_id

    @property
    def is_authenticated(self) -> bool:
        """
        Checks if the user is authenticated. This method essentially does nothing,
        but it could implement session logic for example.
        """
        return True

    @property
    def display_name(self) -> str:
        """Display name of the user"""
        return f"{self.first_name} {self.last_name}"

    @property
    def identity(self) -> str:
        """Identification attribute of the user"""
        return self.user_id
