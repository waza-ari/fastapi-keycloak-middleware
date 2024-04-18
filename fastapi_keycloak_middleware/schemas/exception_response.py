"""
Pydantic schema used to represent an exception response.
"""

from pydantic import BaseModel


class ExceptionResponse(BaseModel):
    """
    Schema used to describe an exception response
    """

    detail: str | None = None
