"""
This module contains the default representation of a service principal

It is used if no custom service mapper is provided to map the token claims
of a service (client credentials) token to an application specific object.
"""

from starlette.authentication import BaseUser


class ServicePrincipal(BaseUser):
    """Service principal identified by the client ID the token was issued to"""

    def __init__(self, client_id: str):
        """
        ServicePrincipal Constructor
        """
        self.client_id = client_id

    def __repr__(self) -> str:
        return f"ServicePrincipal(client_id={self.client_id!r})"

    @property
    def is_authenticated(self) -> bool:
        """Service principals are always authenticated"""
        return True

    @property
    def display_name(self) -> str:
        """Display name of the service, the client ID"""
        return self.client_id

    @property
    def identity(self) -> str:
        """Identification attribute of the service, the client ID"""
        return self.client_id
