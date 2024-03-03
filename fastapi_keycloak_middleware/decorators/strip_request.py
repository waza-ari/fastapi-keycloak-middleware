"""
Convenience wrapper that handles removing the request argument from the function
arguments if needed. As the actual function does not include the argument, it
would lead to a Python exception if the argument is not removed.

This wrapper will check if the function contains the request argument and if
not, will remove it from kwargs before calling the function.
"""

from functools import wraps
from inspect import signature


def strip_request(func):
    """
    Wrapper that strips the request argument from kwargs
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        parameters = signature(func).parameters
        if "request" in parameters.keys():
            return await func(*args, **kwargs)

        if "request" in kwargs:
            del kwargs["request"]
        return await func(*args, **kwargs)

    return wrapper
