Authorization
=============

Authorization is about enforcing certain permissions to certain resources. In this
case a resource is a FastAPI endpoint, but there's also a concept to enforce more
fine grained controls, also that needs to be done within your code.

Used Nomenclature
^^^^^^^^^^^^^^^^^

In this document, the following nomenclature is used. Note that especially the Scope and Permission definition does not neccessarily match the definition in the OAuth2 specification.

* **Resource**: A resource is a FastAPI endpoint.
* **Resource Server (RS)**: The resource server is the FastAPI application.
* **Access Token (AT)**: Token send by the user to the resource server.
* **Claim**: Part of the AT that contains information about the user.
* **Scope**: Information obtained from the chosen authorization method (e.g. based on a :code:`roles` claim within the AT). Generally, this is just a list of strings
* **Permissions**: Your application has the option to map the scopes to permissions. This is done by providing a mapper function. If you don't provide one, the scopes will be passed as is and used for permissions.

Overview
^^^^^^^^

In general, the folowing process is followed:

#. A user is authenticated.
#. Based on the chosen authorization method, the Scope is compiled. Currently, only claim based scopes are supported (that is, the information is extracted from a claim), but there are plans to add Keycloaks fine grained permissions system at a later time.
#. A mapper is applied to map the obtained Scope to Permissions. For example, if your AT containes the :code:`roles` claim, you can map these roles to permissions.
#. A decorator is used on the FastAPI endpoint to enforce a certain permission.
#. Optionally, you can get the result of the permission evaluation as dependency and can work with it to ensure a more fine grained control.

Basic Usage
^^^^^^^^^^^

This is a basic example of how to use the authorization system. It is based on the :ref:`usage` example.

Enable Authorization
""""""""""""""""""""

To enable authorization, simply pass the chosen method to the middleware initialization:

.. code-block:: python

    from fastapi import FastAPI
    from fastapi_keycloak_middleware import KeycloakConfiguration, AuthorizationMethod, setup_keycloak_middleware

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        authorization_method=AuthorizationMethod.CLAIM,
    )

    app = FastAPI()

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
    )

Protect Endpoint
""""""""""""""""

Then, on the endpoint you want to protect, add a dependency specifying which permission is required to access the resource:

.. code-block:: python

    from fastapi import Depends
    from fastapi_keycloak_middleware import CheckPermissions

    @app.get("/protected", dependencies=[Depends(CheckPermissions("protected"))])
    def protected():
        return {"message": "Hello World"}

.. note::
   Previous versions of the library used the :code:`@require_permission` decorator. This has been deprecated in favor of the :code:`CheckPermissions` dependency, please update your code accordingly.

Claim Authorization
^^^^^^^^^^^^^^^^^^^

As of today, the authorization based on a claim is the only supported method. This means that the scopes are extracted from a claim within the AT. 

By default, the :code:`roles` claim will be checked to build the scope. You can configure this behavior:

.. code-block:: python
    :emphasize-lines: 4

    keycloak_config = KeycloakConfiguration(
        # ...
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="permissions"
    )

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
    )

In this example, the library would extract the scopes from the :code:`permissions` claim.

Permission Mapping
^^^^^^^^^^^^^^^^^^

In the examples above, the content of the claims is used unmodified. You can add a custom mapper to map the scopes to permissions. A common example for this is mapping **roles** to **permissions**. This is done by providing a mapper function:

.. code-block:: python
    :emphasize-lines: 29

    from fastapi import FastAPI
    from fastapi_keycloak_middleware import KeycloakConfiguration, AuthorizationMethod, setup_keycloak_middleware

    async def scope_mapper(claim_auth: typing.List[str]) -> typing.List[str]:
        """
        Map token roles to internal permissions.

        This could be whatever code you like it to be, you could also fetch this
        from database. Keep in mind this is done for every incoming request though.
        """
        permissions = []
        for role in claim_auth:
            try:
                permissions += rules[role]
            except KeyError:
                log.warning("Unknown role %s" % role)

        return permissions

    keycloak_config = KeycloakConfiguration(
        # ...
        authorization_method=AuthorizationMethod.CLAIM,
    )

    setup_keycloak_middleware(
        app,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
        scope_mapper=scope_mapper,
    )

The result of this mapping function is then used to enforce the permissions.

Composite Authorization
^^^^^^^^^^^^^^^^^^^^^^^

You can build more complex authorization rules by combining multiple permissions. This is done by passing a list of permissions to the :code:`CheckPermissions` method:

.. code-block:: python
    :emphasize-lines: 4

    from fastapi import Depends
    from fastapi_keycloak_middleware import CheckPermissions

    @app.get("/view_user", dependencies=[Depends(CheckPermissions(["user:view", "user:view_own"]))])
    def view_user():
        return {"userinfo": "Hello World"}

By default, the decorator will now enforce that the user bas both permissions. You can change this behavior by passing the :code:`match_strategy` parameter:

.. code-block:: python
    :emphasize-lines: 2,4

    from fastapi import Depends
    from fastapi_keycloak_middleware import CheckPermissions, MatchStrategy

    @app.get("/view_user", dependencies=[Depends()])
    def view_user():
        return {"userinfo": "Hello World"}

Now, it is sufficient for the user to have one of the mentioned permissions.

Accessing the Authorization Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The method itself works like a regular FastAPI dependency and can be used either in the :code:`dependencies` parameter of the endpoint or as a parameter to the path function.
When used as a parameter, the result of the authorization evaluation is passed to the function.

.. code-block:: python
    :emphasize-lines: 2,5

    from fastapi import Depends
    from fastapi_keycloak_middleware import AuthorizationResult, CheckPermissions, MatchStrategy

    @app.get("/view_user")
    def view_user(authorization_result: AuthorizationResult = Depends(CheckPermissions(["user:view", "user:view_own"], match_strategy=MatchStrategy.OR))):
        return {"userinfo": "Hello World"}

You can now access the permissions that actually matched and act based on this information. For example, if only the :code:`user:view_own` permission matched, you could check if the user requested matches the currently logged in user.

.. note::
   Note that previous versions of this library used a decorator to match permissions and therefore needed quite convoluted logic to make the result accessible. Using the :code:`@require_permission` decorator and therefore the :code:`get_authorization_result` dependency is deprecated and will be removed in future versions.
