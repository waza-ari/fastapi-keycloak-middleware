"""
This module contains the rule used to exclude requests from authentication.
"""

import re
import typing
from dataclasses import dataclass, field

from starlette.types import Scope


@dataclass(frozen=True)
class ExcludeRule:
    """
    A rule that excludes matching requests from authentication. All given criteria
    must match for a request to be excluded.

    :param path: Regular expression that must match the **entire** request path,
        e.g. ``r"/users/[0-9]+/avatar"``. Mutually exclusive with ``prefix``.
    :type path: str, optional
    :param prefix: Literal path prefix, matched on whole path segments: ``"/docs"``
        matches ``/docs`` and ``/docs/oauth2-redirect``, but not ``/docs-admin``.
        Mutually exclusive with ``path``.
    :type prefix: str, optional
    :param methods: HTTP methods the rule applies to, e.g. ``{"POST"}``. Defaults to
        all methods. ``GET`` includes ``HEAD``, as Starlette routes and static files
        answer ``HEAD`` requests for ``GET`` endpoints. Rules with methods never match
        websocket connections.
    :type methods: typing.Iterable[str], optional
    """

    path: str | None = None
    prefix: str | None = None
    methods: typing.Iterable[str] | None = None
    _path_regex: re.Pattern | None = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        if self.path is not None and self.prefix is not None:
            raise ValueError("ExcludeRule accepts either path or prefix, not both")
        if self.path is None and self.prefix is None and not self.methods:
            raise ValueError("ExcludeRule requires a path, a prefix or methods")

        if self.path is not None:
            try:
                object.__setattr__(self, "_path_regex", re.compile(self.path))
            except re.error as exc:
                raise ValueError(
                    f"Invalid regular expression in exclude rule: {self.path}"
                ) from exc

        if self.prefix is not None:
            if not self.prefix.startswith("/"):
                raise ValueError(f"Exclude prefix must start with '/': {self.prefix}")
            # A trailing slash makes no difference, matching is done on whole segments
            object.__setattr__(self, "prefix", self.prefix.rstrip("/"))

        if self.methods is not None:
            methods = {method.upper() for method in self.methods}
            if "GET" in methods:
                methods.add("HEAD")
            object.__setattr__(self, "methods", frozenset(methods))

    def matches(self, scope: Scope) -> bool:
        """
        Checks whether the request described by the ASGI scope matches this rule.

        :param scope: The ASGI scope of the request
        :type scope: Scope
        :return: True if the request should be excluded from authentication
        :rtype: bool
        """
        if self.methods is not None and scope.get("method") not in self.methods:
            return False

        path = scope["path"]
        if self._path_regex is not None:
            return self._path_regex.fullmatch(path) is not None
        if self.prefix is not None:
            return path == self.prefix or path.startswith(self.prefix + "/")
        return True
