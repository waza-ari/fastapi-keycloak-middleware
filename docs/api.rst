API Documentation
=================

.. module:: fastapi_keycloak_middleware

This part of the documentation covers all the interfaces of Requests. For
parts where Requests depends on external libraries, we document the most
important right here and provide links to the canonical documentation.

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
.. autoclass:: AuthorizationResult
    :members:
.. autoclass:: AuthorizationMethod
    :members:
.. autoclass:: MatchStrategy
    :members:

Decorators
----------

These decorators can be used to wrap certain paths in your FastAPI application.

.. autofunction:: require_permission
.. autofunction:: strip_request

FastAPI Depdencies
------------------

These are the dependencies that you can use in your FastAPI application.

.. autofunction:: get_user
.. autofunction:: get_authorization_result
