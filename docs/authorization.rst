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
    from fastapi_keycloak_middleware import KeycloakConfiguration, KeycloakMiddleware, AuthorizationMethod

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
    )

    app = FastAPI()

    app.add_middleware(
        KeycloakMiddleware,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
        authorization_method=AuthorizationMethod.CLAIM,
    )

Protect Endpoint
""""""""""""""""

Then, on the endpoint you want to protect, use the :code:`@require_permission` decorator:

.. code-block:: python

    from fastapi_keycloak_middleware import require_permission

    @app.get("/protected")
    @require_permission("protected")
    def protected():
        return {"message": "Hello World"}

.. note::
   The more experienced FastAPI users may notice that we're not passing the :code:`Request` parameter to the path function, even though the decorator requires this. If you're interested in how that works under the hood, check the :ref:`advanced_topics` section for a more in-depth explanation.

Claim Authorization
^^^^^^^^^^^^^^^^^^^

As of today, the authorization based on a claim is the only supported method. This means that the scopes are extracted from a claim within the AT. 

By default, the :code:`roles` claim will be checked to build the scope. You can configure this behavior:

.. code-block:: python
    :emphasize-lines: 6

    app.add_middleware(
        KeycloakMiddleware,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim="permissions"
    )

In this example, the library would extract the scopes from the :code:`permissions` claim.

You can also provide a custom claim path with the :code:`authorization_claim_path` parameter. 
This is useful if the claim is nested within the payload.

.. code-block:: python
    :emphasize-lines: 6

    app.add_middleware(
        KeycloakMiddleware,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
        authorization_method=AuthorizationMethod.CLAIM,
        authorization_claim_path=["realm_access", "roles"]
    )

This would extract the scopes from the :code:`roles` claim nested within the :code:`realm_access` claim.
.. code-block:: json
    
    "claimX": "",
    "realm_access": {
        "roles": [
            "supporter",
            "admin",
            "user"
        ]
    },
    "claimY": "",

It will prefer the :code:`authorization_claim_path` parameter over the :code:`authorization_claim` parameter if both are provided.

Permission Mapping
^^^^^^^^^^^^^^^^^^

In the examples above, the content of the claims is used unmodified. You can add a custom mapper to map the scopes to permissions. A common example for this is mapping **roles** to **permissions**. This is done by providing a mapper function:

.. code-block:: python
    :emphasize-lines: 23

    from fastapi import FastAPI
    from fastapi_keycloak_middleware import KeycloakConfiguration, KeycloakMiddleware, AuthorizationMethod

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

    app.add_middleware(
        KeycloakMiddleware,
        keycloak_configuration=keycloak_config,
        get_user=auth_get_user,
        scope_mapper=scope_mapper,
        authorization_method=AuthorizationMethod.CLAIM,
    )

The result of this mapping function is then used to enforce the permissions.

Composite Authorization
^^^^^^^^^^^^^^^^^^^^^^^

You can build more complex authorization rules by combining multiple permissions. This is done by passing a list of permissions to the :code:`@require_permissions` decorator:

.. code-block:: python
    :emphasize-lines: 4

    from fastapi_keycloak_middleware import require_permission

    @app.get("/view_user")
    @require_permission(["user:view", "user:view_own"])
    def view_user():
        return {"userinfo": "Hello World"}

By default, the decorator will now enforce that the user bas both permissions. You can change this behavior by passing the :code:`match_strategy` parameter:

.. code-block:: python
    :emphasize-lines: 1,4

    from fastapi_keycloak_middleware import require_permission, MatchStrategy

    @app.get("/view_user")
    @require_permission(["user:view", "user:view_own"], match_strategy=MatchStrategy.OR)
    def view_user():
        return {"userinfo": "Hello World"}

Now, it is sufficient for the user to have one of the mentioned permissions.

Accessing the Authorization Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can access the result of the authorization evaluation by using a dependency provided:

.. code-block:: python
    :emphasize-lines: 1,5

    from fastapi_keycloak_middleware import AuthorizationResult, require_permission, MatchStrategy, get_authorization_result

    @app.get("/view_user")
    @require_permission(["user:view", "user:view_own"], match_strategy=MatchStrategy.OR)
    def view_user(authorization_result: AuthorizationResult = Depends(get_authorization_result),):
        return {"userinfo": "Hello World"}

You can now access the permissions that actually matched and act based on this information. For example, if only the :code:`user:view_own` permission matched, you could check if the user requested matches the currently logged in user.
