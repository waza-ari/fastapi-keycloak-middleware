.. _advanced_topics:

Advanced Topics
===============

The following sections describe advanced usage of the library.

Request Modification Details
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If all checks outlined above pass successfully, the actual endpoint (or next middleware) will be called. To persist the authentication result,
we're using the ASGI scope of the request, following the conventions of Starlette. The following keys are added:

**User Object**

The principal returned by the user or service mapper is stored in :code:`scope["user"]`, which is also available as :code:`request.user`.

**Authorization Scopes**

The authorization scopes (after applying the scope mapper) are stored as Starlette :code:`AuthCredentials` in :code:`scope["auth"]`, which is also available as :code:`request.auth`. If authorization is disabled, the list of scopes is empty.

**Authentication Context**

An :code:`AuthContext` is stored in :code:`scope["auth_context"]`. It holds the principal type (user or service), all claims of the access token and the authorization scopes. Use the :code:`get_auth_context` dependency to retrieve it.

Logging
^^^^^^^

Note straight from the `Python Docs <https://docs.python.org/3/howto/logging.html#logging-advanced-tutorial>`_:

.. note:: 
    It is strongly advised that you do not log to the root logger in your library. Instead, use a logger with a unique and easily identifiable name, such as the :code:`__name__` for your library’s top-level package or module. Logging to the root logger will make it difficult or impossible for the application developer to configure the logging verbosity or handlers of your library as they wish.

Also, it is recommended to use module level logging:

.. note::
    A good convention to use when naming loggers is to use a module-level logger, in each module which uses logging, named as follows

This module implements these best practices. 

.. warning::
    Especially during the authorization phase, the user object is included in the log message. Make sure your user object is serializable to a string, otherwise the log message will contain non-helpful strings.

Signing Keys and Key Rotation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tokens are validated locally using the public keys Keycloak publishes for the realm, the JSON Web Key Set
(JWKS) at :code:`/realms/<realm>/protocol/openid-connect/certs`. Each token names the key it was signed with
in the :code:`kid` (key ID) header, which is used to select the key from the set.

The key set is fetched on the first request that needs it, so the application can start while Keycloak is
not reachable. Until the key set could be fetched, requests are answered with :code:`503`.

When the realm keys are rotated in Keycloak, tokens signed with the new key reference a key ID that is not
known yet. The key set is then fetched again, and the token is validated against the new key. The previous
key stays in the key set as long as it is enabled in Keycloak (as passive key), so tokens issued before the
rotation remain valid until they expire. No restart of the application is required.

To prevent tokens with made up key IDs from making the application hammer Keycloak, the key set is fetched
at most once per :code:`jwks_refresh_interval` (30 seconds by default). Failed attempts count as well, the
previously fetched key set stays in use if fetching fails.

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
        jwks_refresh_interval=60,
    )

.. note::
    The key set is only fetched again when a token references an unknown key ID, there is no periodic
    refresh. If the key set was fetched shortly before a new key starts being used, tokens signed with
    the new key are rejected until the refresh interval has passed.

To validate tokens against a fixed key instead, pass it as :code:`key` in the :code:`validation_options`.
The key set is never fetched then:

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
        validation_options={"key": jwk.JWK.from_pem(public_key_pem)},
    )

Token Introspection vs Opaque Tokens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, this library will attempt to validate the JWT signature locally using the public keys obtained from Keycloak. This is the recommended way to validate the token, as it does not require any additional requests to Keycloak. Also, Keycloak does not support opaque tokens yet.

If you want to still use the token endpoint to validate the token, you can opt to do so:

.. code-block:: python
   :emphasize-lines: 7

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        use_introspection_endpoint=True
    )

Please make sure to understand the consequences before applying this configuration.

Disabling Token Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to disable token validation altogether. Be aware that this is a security risk pretty much disables
all security features of the library.

.. code-block:: python
   :emphasize-lines: 7

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        validate_token=False
    )

JWT Decoding Options
^^^^^^^^^^^^^^^^^^^^

The upstream project `python-keycloak` uses `JWCrypto` under the hood to verify
JWT tokens. This library uses sensible defaults for the JWT verification, but it is
possible to modify the decode options if needed.

.. code-block:: python
   :emphasize-lines: 6,7,8

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        # ...
        validation_options={
            "check_claims": {
                "jti": None,
                "exp": None,
                "iat": None,
            }
        }
    )

Please refer to the `JWCrypto` documentation for the available options:
https://jwcrypto.readthedocs.io/en/latest/jwt.html#jwcrypto.jwt.JWT

Validating Issuer and Audience
------------------------------

By default, the signature and the expiry of the token are validated. Tokens issued by the same
realm for other clients are accepted as well. To only accept tokens issued for your API, validate
the :code:`aud` (audience) claim, and optionally the :code:`iss` (issuer) claim:

.. code-block:: python

    keycloak_config = KeycloakConfiguration(
        # ...
        validation_options={
            "check_claims": {
                "iss": "https://sso.your-keycloak.com/realms/<Realm Name>",
                "aud": "my-api",
                "exp": None,
            }
        }
    )

.. warning::
    As soon as :code:`check_claims` is set, `JWCrypto` only checks the claims listed there and
    skips its default checks. Always include :code:`"exp": None`, otherwise expired tokens are
    accepted. Every listed claim must be present in the token, so don't list claims your tokens
    don't contain, such as :code:`nbf`, which Keycloak does not issue.

Keycloak only adds your API to the :code:`aud` claim if the token was requested for it. Add an
*Audience* mapper to the client scope of the clients calling your API, pointing to the client
representing your API.

Excluding Endpoints
^^^^^^^^^^^^^^^^^^^

You may not want to enforce authentication for all endpoints. For example, you may want to allow anonymous access to the health check endpoint or allow accessing the autogenerated docs and OpenAPI schema without authentication.

There are two ways of doing this.

.. note::
    Both examples can also be combined to achieve more complex setups.

Exclude certain paths
---------------------

The middleware provides a configuration option to exclude certain paths from authentication. Those are compiled as regex and then matched against the request path.

**Example:**

.. code-block:: python
    :emphasize-lines: 12

    excluded_routes = [
        "/status",
        "/docs",
        "/openapi.json",
        "/redoc",
    ]

    app = FastAPI()
    setup_keycloak_middleware(
        app,
        # ...
        exclude_patterns=excluded_routes,
    )

This would make sure you can access the docs, alternate docs, OpenAPI schema and health check endpoint without authentication.

.. warning::
    At the moment only the paths are checked, not the request method or other criteria. See issue `#3 <https://github.com/waza-ari/fastapi-keycloak-middleware/issues/3>`_ for more details.

**Technical Details:**

Under the hood these paths are compiled to regex and then matched against the request path. Each string is passed as-is to :code:`re.compile` and stored, such that it can be used later to patch against the request path.

Use Multiple Applications
-------------------------

Alternatively you can use multiple :code:`FastAPI` applications and mount them to the main application. This way you can have different authentication requirements for different endpoints.

**Example:**

.. code-block:: python

    # This first app is secured
    secured_app = FastAPI()

    setup_keycloak_middleware(
        secured_app,
        # ...
        exclude_patterns=excluded_routes,
    )

    # This second app has no middleware to it and is not protected
    public_app = FastAPI()

    # This is your main app, mounting the other two applications
    app = FastAPI()
    app.mount(path="/secured", app=secured_app)
    app.mount(path="/public", app=public_app)

.. _service_principals:

Service Principals
^^^^^^^^^^^^^^^^^^

Besides users, your API may be called by other software: IoT devices, background jobs or other backends.
These usually authenticate using the OAuth 2.0 *client credentials* grant, which issues a token to the
client itself, without any user being involved. This library calls them **service principals**.

User Devices
------------

Devices that act on behalf of a user are not service principals. You can use the Keycloak
`device authorization grant <https://www.keycloak.org/docs/latest/securing_apps/#device-authorization-grant>`_:
the device shows a code to the user, who enters it in Keycloak and authenticates with the user credentials.
The device then receives a token for that user. For this library there is no difference between those tokens
and regular user tokens, so authentication and authorization work as previously described.

Detecting Service Tokens
------------------------

Identity providers mark service tokens differently, so the library lets you decide which tokens belong to
a service. Pass a :code:`service_detector` function, it receives all claims of the validated token and
returns :code:`True` for service tokens:

.. code-block:: python

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        service_detector=lambda claims: bool(claims.get("is_device")),
    )

If no detector is configured, every token is treated as a user token. Some common detectors:

.. list-table::
   :header-rows: 1

   * - Identity provider
     - Detector
   * - Explicit claim, e.g. a Keycloak *Hardcoded claim* mapper on the client
     - :code:`lambda c: bool(c.get("is_device"))`
   * - Keycloak service accounts
     - :code:`lambda c: c.get("preferred_username", "").startswith("service-account-")`
   * - RFC 9068 compliant providers
     - :code:`lambda c: c.get("sub") == c.get("client_id")`
   * - Auth0
     - :code:`lambda c: c.get("gty") == "client-credentials"`
   * - Microsoft Entra ID
     - :code:`lambda c: c.get("idtyp") == "app"`

.. warning::
    Only rely on claims that cannot be influenced by users. For example, don't detect services based on a
    user attribute that users can edit themselves.

Mapping Service Tokens
----------------------

Service tokens are passed to the :code:`service_mapper` instead of the :code:`user_mapper`. It receives all
claims of the token and returns an object representing the service. By default, a :code:`ServicePrincipal`
is returned, identified by the :code:`client_id` claim, or the :code:`azp` or :code:`sub` claim if not present.

Like the user mapper, returning :code:`None` or raising an exception rejects the request with a :code:`401`
response. This allows you to deactivate a single service immediately:

.. code-block:: python

    async def map_service(claims: dict[str, typing.Any]) -> ServiceClient | None:
        """
        Look up the calling client in the database. Unknown or disabled clients are rejected.
        """
        return await ServiceClient.get_enabled(client_id=claims["azp"])

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        user_mapper=map_user,
        service_mapper=map_service,
        service_detector=lambda claims: bool(claims.get("is_device")),
    )

.. note::
    Disabling the client in Keycloak only prevents new tokens from being issued, tokens already issued
    remain valid until they expire. Rejecting the client in the service mapper closes this gap.

Authorization scopes are extracted and mapped the same way as for users, so :code:`CheckPermissions`
works for services as well. The required claims (see :code:`required_claims`) apply to service
tokens too.

Using Service Principals in Endpoints
-------------------------------------

Use the dependency matching what the endpoint needs:

* :code:`get_user` for endpoints that need a user. Service tokens get a :code:`403` response.
* :code:`get_service_principal` for endpoints that only services call. User tokens get a :code:`403` response.
* :code:`get_principal` for endpoints that serve both. Use :code:`isinstance` on the returned object, or
  :code:`get_auth_context` to check the principal type.

Prefer returning a distinct type from the service mapper over making services look like users. Code that
needs user specific data then can't receive a service by accident.

Keycloak Configuration
----------------------

One example on how to configure Keycloak for service principals:

1. Create one confidential client per service and enable *Service accounts roles* (client credentials grant).
   Disable the other flows if the client is not used otherwise.
2. Assign roles to the service account of the client. Map them to the same claim you use for user roles,
   so the scope mapper can handle both.
3. Optionally, add a *Hardcoded claim* mapper to the client, e.g. :code:`is_device` with value :code:`true`,
   and use it in the :code:`service_detector`.
4. Optionally, add an *Audience* mapper pointing to your API, and validate the audience as described in
   `Validating Issuer and Audience`_.

Rotating the client secret of one service does not affect the others.

Websocket Support
^^^^^^^^^^^^^^^^^

We can also inspect websocket connection requests and validate the token using the same mechanisms. Websockets do not support the same headers, therefore we have to use cookies instead.
Websocket support is enabled by default, but can be disabled by setting the :code:`enable_websocket_support` parameter to :code:`False`.

If enabled, the initial websocket connection request will be validated, subsequent messages within the same socket won't be affected.
The cookie is expected to be named :code:`access_token` and contain the JWT token prefixed with :code:`Bearer`.
