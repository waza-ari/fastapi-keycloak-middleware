Migrating to 2.0
================

Version 2.0 introduces service principals, removes the deprecated decorator API and cleans up
the configuration. This guide lists all breaking changes and how to update your application.

Requirements
^^^^^^^^^^^^

2.0 requires :code:`python-keycloak` 4.7.3 or newer. Earlier releases are not compatible with
:code:`httpx` 0.28 and newer, they fail to create a Keycloak client.

Configuration
^^^^^^^^^^^^^

:code:`KeycloakConfiguration` now rejects unknown options, so options removed in 2.0 raise a
validation error instead of being silently ignored.

.. list-table::
   :header-rows: 1

   * - 1.x
     - 2.0
   * - :code:`claims`, :code:`reject_on_missing_claim`
     - :code:`required_claims`, defaults to :code:`["sub"]`. The mappers receive all claims of the token.
   * - :code:`enable_device_authentication`, :code:`device_authentication_claim`
     - :code:`service_detector` and :code:`service_mapper` arguments of :code:`setup_keycloak_middleware`,
       see below.

In 1.x, tokens without :code:`name`, :code:`family_name`, :code:`given_name`, :code:`preferred_username`
or :code:`email` were rejected by default. In 2.0 only :code:`sub` is required. If your user mapper relies on
other claims, add them to :code:`required_claims`:

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
        required_claims=["sub", "email"],
    )

User Mapper
^^^^^^^^^^^

The user mapper receives all claims of the access token instead of only the configured ones. Existing
mappers keep working, as the dictionary is a superset of what they received before. Claims that are not
listed in :code:`required_claims` may be missing.

The default user mapper now sets :code:`FastApiUser.identity` to the :code:`sub` claim. In 1.x it was
always empty.

Device Authentication
^^^^^^^^^^^^^^^^^^^^^

Device tokens are now called service tokens and are no longer passed through with :code:`user` set to
:code:`None`. Instead, they are mapped by a service mapper, the same way user tokens are mapped by the
user mapper. See :ref:`service_principals` for details.

1.x:

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
        enable_device_authentication=True,
        device_authentication_claim="is_device",
    )

    setup_keycloak_middleware(app, keycloak_configuration=keycloak_config, user_mapper=map_user)

2.0:

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
    )

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        user_mapper=map_user,
        service_detector=lambda claims: bool(claims.get("is_device")),
        # Optional, defaults to returning a ServicePrincipal
        service_mapper=map_service,
    )

Other differences to the 1.x device authentication:

* Service tokens must contain the :code:`required_claims` as well. Keycloak service account tokens contain
  :code:`sub`, so the default works.
* Only tokens where the detector returns :code:`True` are service tokens. In 1.x, a token containing the device
  claim with a falsy value was passed to the user mapper with only the device claim.
* :code:`request.user` holds the object returned by the service mapper instead of :code:`None`. If your code
  used :code:`user is None` to detect devices, use :code:`get_service_principal`, :code:`isinstance` or the
  principal type of the :code:`AuthContext` instead.

Dependencies
^^^^^^^^^^^^

* :code:`get_user` responds with :code:`401` if the request is not authenticated and with :code:`403` if the
  token was issued to a service. In 1.x it returned :code:`None` or the device user. Use :code:`get_principal`
  for endpoints that serve both users and services.
* :code:`get_auth` returns an empty list instead of :code:`None` if there are no scopes.
* :code:`CheckPermissions` no longer depends on :code:`get_user`. It only depends on :code:`get_auth`, and
  responds with :code:`403` if there are no scopes, e.g. on paths excluded from authentication.
* New dependencies: :code:`get_principal`, :code:`get_service_principal` and :code:`get_auth_context`.

Removed Decorators
^^^^^^^^^^^^^^^^^^

The :code:`require_permission` and :code:`strip_request` decorators and the :code:`get_authorization_result`
dependency have been removed. Use the :code:`CheckPermissions` dependency instead.

1.x:

.. code-block:: python

    @app.get("/users")
    @require_permission(["user:view", "user:view_own"], match_strategy=MatchStrategy.OR)
    async def view_users(authorization_result: AuthorizationResult = Depends(get_authorization_result)):
        ...

2.0:

.. code-block:: python

    @app.get("/users")
    async def view_users(
        authorization_result: AuthorizationResult = Depends(
            CheckPermissions(["user:view", "user:view_own"], match_strategy=MatchStrategy.OR)
        ),
    ):
        ...

Request Scope
^^^^^^^^^^^^^

* :code:`scope["auth"]` holds Starlette :code:`AuthCredentials` instead of a list. Use :code:`get_auth`, or
  :code:`request.auth.scopes` if you accessed the scope directly.
* :code:`scope["auth_context"]` is new and holds an :code:`AuthContext`.

Error Responses
^^^^^^^^^^^^^^^

* All :code:`401` responses include a :code:`WWW-Authenticate` header (RFC 6750).
* A missing claim results in :code:`401` with the detail :code:`The access token is missing the claim '<claim>'`
  instead of a generic error.
* If Keycloak can't be reached during token introspection, the response is :code:`503` instead of :code:`401`.
* When using the introspection endpoint, tokens reported as inactive are rejected. In 1.x, they were only
  rejected if a required claim was missing.

Signing Keys
^^^^^^^^^^^^

Tokens are validated against the realm key set (JWKS) instead of the single active public key, so rotating
the realm keys no longer requires restarting the application. See :doc:`advanced_topics` for details.

* The key set is fetched on the first request instead of when the middleware is created. A Keycloak server
  that is not reachable no longer prevents the application from starting, requests are answered with
  :code:`503` until the key set could be fetched.
* :code:`KeycloakBackend.public_key` has been removed.
* A :code:`key` in :code:`validation_options` is used instead of the realm keys. In 1.x, this raised an
  error on every request.
* :code:`validation_options` accepts any value. In 1.x, keys were silently converted to plain dictionaries,
  and options like a list of audiences were rejected.

Other Changes
^^^^^^^^^^^^^

* :code:`ExceptionResponse` can be imported from :code:`fastapi_keycloak_middleware` directly.
* Websocket connections are detected by the ASGI scope type instead of the :code:`Upgrade` header.
* :code:`authorization_claim` and :code:`required_claims` support dot separated paths into nested claims,
  e.g. :code:`realm_access.roles`, and space delimited strings like the :code:`scope` claim are split into a
  list of scopes. See :doc:`authorization`.
