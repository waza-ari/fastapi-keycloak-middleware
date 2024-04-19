.. _usage:

Usage Guide
===========

Basic Example
^^^^^^^^^^^^^

This is a very basic example on how to add the Middleware to a FastAPI application. All (full) examples are complete as is and can be run without modification.

.. code-block:: python

   from fastapi import FastAPI
   from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware

   # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
    )

    app = FastAPI()

    # Add middleware with basic config
    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
    )

    @app.get("/")
    async def root():
        return {"message": "Hello World"}


This is a minimal example of using the middleware and will already perform the following actions:

* Parse the :code:`Authorization` header for a :code:`Bearer` token (the token scheme can be configured, see below). Return :code:`401` if no token is found.
* Validate the token using the public key of the realm obtained from Keycloak. Return :code:`401` if the token is invalid or expired.
* Extract user information from the token. The claims to use are configurable, by default the following claims are read:
   * :code:`sub` - part of the :code:`openid` scope, defining a mandatory, unique, immutable string identifier for the user
   * :code:`name` - part of the :code:`profile` scope, defining a human-readable name for the user
   * :code:`family_name` - part of the :code:`profile` scope, defining the user's family name
   * :code:`given_name` - part of the :code:`profile` scope, defining the user's given name
   * :code:`preferred_username` - part of the :code:`profile` scope, defining the user's preferred username. Note that as per openid specifications, you must not rely on this claim to be unique for all users
   * :code:`email` - part of the :code:`email` scope, defining the user's email address
* Get the user object based on the extracted information. As no custom callback function is provided, it will return an instance of :code:`FastApiUser` containing extracted information.
* Add proper 401 and 403 responses to the OpenAPI schema

.. note::
   **Authorization** is disabled by default, so no authorization scopes will be stored.

Keycloak Configuration Scheme
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :code:`KeycloakConfiguration` class is used to configure the Keycloak connection. Refer to the :ref:`Classes API documentation<keycloak_configuration>` for a complete list of parameters that are supported.

Change Authentication Scheme
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The authentication scheme is essentially the prefix of the :code:`Authorization` header. By default, the middleware will look for a :code:`Bearer` token. This can be changed by setting :code:`authentication_scheme` attribute of the :code:`KeycloakConfiguration` class:

.. code-block:: python
   :emphasize-lines: 7

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        authentication_scheme="Token"
    )

This example will accept headers like :code:`Authorization: Token <token>` instead of :code:`Bearer`.

Customize User Getter
^^^^^^^^^^^^^^^^^^^^^

By default an instance of :code:`FastApiUser` will be returned. Refer to the API documentation for details about the information stored in this class.

In many cases, you'll have your own user model you want to work with and therefore would like to return your own user object. This can be done by providing a custom callback function to the :code:`user_mapper` parameter of the middleware initialization class:

.. code-block:: python
   :emphasize-lines: 1,2,3,9

   async def map_user(userinfo: typing.Dict[str, typing.Any]) -> User:
       # Do something with the userinfo
       return User()

    # Add middleware with basic config
    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        user_mapper=map_user,
    )

The :code:`userinfo` parameter is a dictionary containing the claims extracted from the access token. You can rely on all the claims to be populated, as tokens without these claims are rejected in a previous step by default. This behavior can be changed by setting the :code:`reject_on_missing_claim` parameter of the :code:`KeycloakConfiguration` class to :code:`False`, then you need to handle potentially missing claims yourself.

This is an example of what you can expect using the default configuration:

.. code-block:: json

   {
       "sub": "1234567890",
       "name": "John Doe",
       "family_name": "Doe",
       "given_name": "John",
       "preferred_username": "jdoe",
       "email": "jon.doe@example.com"
    }

.. note::
   Depending on your application architecture, you can of course also use this method to create the user, if users are allowed to **register** (not just authenticate) to your application via Keycloak.

**Rejecting on missing claims**

If you opt to allow missing claims, you can still reject the user authentication within your :code:`get_user` class by simply returning :code:`None`.

**Database / ORM mappings**

Be careful when working with ORM tools like SQLAlchemy. Assume you're adding an ORM mapped model here, the association to the database session would be lost when using it within the FastAPI endpoint later. This means that accessing attributes which have not been loaded yet (lazy loading) would lead to an exception being raised. In such a scenario, you can opt for pre-planning and eager load the required attributes, but it might be better to simply store a unique identifier to the user here and use this to retrieve the user object later using dependencies. See the following sections for details.

Getting the User in FastAPI Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This package provides a very simple dependency to retrieve the user object from the request. This is useful for simple cases, but for more advanced cases you may want to provide your own dependency.

**Simple Example**

.. code-block:: python

    from fastapi_keycloak_middleware import get_user

    @app.get("/")
    async def root(user: User = Depends(get_user)):
        return {"message": "Hello World"}

This will return whatever was stored in the request either by the built-in function or your custom function to retrieve the user object.

**Advanced Example**

Now assume you've not stored a model here but some unique identifier, to avoid the lazy loading issue mentioned above. You can then use this to retrieve the user object from the database using a dependency:

.. code-block:: python

    def get_user(request: Request, db: Session = Depends(get_db)):
        """
        Custom dependency to retrieve the user object from the request.
        """

        if "user" in request.scope:
            # Do whatever you need to get the user object from the database
            user = User.get_by_id(db, request.scope["user"].id)
            if user:
                return user

        # Handle missing user scenario
        raise HTTPException(
            status_code=401,
            detail="Unable to retrieve user from request",
        )

    @app.get("/")
    async def root(user: User = Depends(get_user)):
        return {"message": "Hello World"}

This will give you a user object that is still bound to the database session, so you can work with it like with any other ORM object.

.. note::
    :code:`get_db` is assumed to be an existing dependency to retrieve a Session to your database.

Modify Extracted Claims
^^^^^^^^^^^^^^^^^^^^^^^

You can also configure the class to extract other / additional claims from the token and pass it to the :code:`user_mapper` function:

.. code-block:: python
   :emphasize-lines: 7

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        claims=["sub", "name", "email", "your-claim"], # Modify claims
        reject_on_missing_claim=False, # Control behaviour when claims are missing
    )

Swagger UI Integration
^^^^^^^^^^^^^^^^^^^^^^

It is also possible to configure the Swagger UI to display endpoints being protected by this middleware correctly
and handle authentication to test the endpoints. This has not been in place in earlier versions, so it is disabled
by default for now.

To enable this feature, you need to set :code:`add_swagger_auth` flag to :code:`True` when configuring the middleware.
Also, it is recommended to setup a separate Keycloak client for this purpose, as it should be a public client. This
separate client is then configured using the :code:`swagger_client_id`  parameter of :code:`KeycloakConfiguration`.

.. code-block:: python
   :emphasize-lines: 6,7,8,9,15

    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        swagger_client_id="<Swagger Client ID>",
        swagger_auth_scopes=["openid", "profile"], # Optional
        swagger_auth_pkce=True, # Optional
        swagger_scheme_name="keycloak" # Optional
    )

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        add_swagger_auth=True
    )

There are three more parameters that can be used to customize the Swagger UI integration:

* :code:`swagger_auth_scopes` - The scopes that should be selected by default when hitting the Authorize button in Swagger UI. Defaults to :code:`['openid', 'profile']`
* :code:`swagger_auth_pkce` - Whether to use PKCE for the Swagger UI client. Defaults to :code:`True`. It is recommended to use Authorization Code Flow with PKCE for public clients instead of implicit flow. In Keycloak, this flow is called "Standard flow"
* :code:`swagger_scheme_name` - The name of the OpenAPI security scheme. Usually there is no need to change this.

Full Example
^^^^^^^^^^^^

Everything combined might look like the following. Important note: the KeycloakConfiguration.verify attribute maps to the 
[KeycloakOpenID](https://github.com/marcospereirampj/python-keycloak/blob/5957607ad07536b94d878c3ce5d403c212b35220/src/keycloak/keycloak_openid.py#L62) verify
attribute, which must be the True or False bool or the str path to the CA bundle used for the cert. The default KeycloakConfiguration.verify value is True.

.. code-block:: python

    from fastapi import FastAPI
    from fastapi_keycloak_middleware import KeycloakConfiguration, setup_keycloak_middleware

    # Set up Keycloak connection
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        claims=["sub", "name", "email", "your-claim"], # Modify claims
        reject_on_missing_claim=False, # Control behaviour when claims are missing
        verify="<Path to CA File>/ca.pem" # Can be True, False or the path to the CA file used to sign certs
    )

    async def map_user(userinfo: typing.Dict[str, typing.Any]) -> User:
        """
        Map userinfo extracted from the claim
        to something you can use in your application.

        You could
        - Verify user presence in your database
        - Create user if it doesn't exist (depending on your application architecture)
        """
       user = make_sure_user_exists(userinfo) # Replace with your logic
       return user

    def get_user(request: Request, db: Session = Depends(get_db)):
        """
        Custom dependency to retrieve the user object from the request.
        """

        if "user" in request.scope:
            # Do whatever you need to get the user object from the database
            user = User.get_by_id(db, request.scope["user"].id)
            if user:
                return user

        # Handle missing user scenario
        raise HTTPException(
            status_code=401,
            detail="Unable to retrieve user from request",
        )

    app = FastAPI()

    # Add middleware with basic config
    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        user_mapper=map_user,
    )

    @app.get("/")
    async def root(user: User = Depends(get_user)):
        return {"message": "Hello World"}
