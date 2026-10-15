API Documentation
=================

.. module:: fastapi_keycloak_middleware

This part of the documentation covers all public interfaces of the library.

Middleware
----------

.. autofunction:: setup_keycloak_middleware
.. autoclass:: KeycloakMiddleware
    :members:

Support Classes
---------------

.. _keycloak_configuration:
.. autoclass:: KeycloakConfiguration
    :members:
.. autoclass:: ExcludeRule
.. autoclass:: AuthContext
    :members:
.. autoclass:: PrincipalType
    :members:
.. autoclass:: FastApiUser
    :members:
.. autoclass:: ServicePrincipal
    :members:
.. autoclass:: AuthorizationResult
    :members:
.. autoclass:: AuthorizationMethod
    :members:
.. autoclass:: MatchStrategy
    :members:
.. autoclass:: ExceptionResponse
    :members:

FastAPI Dependencies
--------------------

These are the dependencies that you can use in your FastAPI application.

.. autoclass:: CheckPermissions
    :members: __init__
.. autofunction:: get_principal
.. autofunction:: get_user
.. autofunction:: get_service_principal
.. autofunction:: get_auth
.. autofunction:: get_auth_context
