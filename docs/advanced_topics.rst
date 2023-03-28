.. _advanced_topics:

Advanced Topics
===============

The following sections describe advanced usage of the library.

Request Modification Details
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If all checks outlined above pass successfully, the actual endpoint (or next middleware) will be called. To persist the authentication result,
we're using Starlettes :code:`Request` object. The following attributes are added to the request:

**User Object**

The user object is stored in :code:`scope.user` attribute. As the request is passed to further middlewares, dependencies or potentially decorators, the endpoint can access the user information.

**Authorization Scopes**

This example does not contain any scopes, so the :code:`scope.auth` attribute will be an empty list. Refer to the advanced documentation for how to leverate authorization scopes.

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

Token Introspection vs Opaque Tokens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, this library will attempt to validate the JWT signature locally using the public key obtained from Keycloak. This is the recommended way to validate the token, as it does not require any additional requests to Keycloak. Also, Keycloak does not support opaque tokens yet.

If you want to still use the token endpoint to validate the token, you can opt to do so:

.. code-block:: python
   :emphasize-lines: 7

    # Set up Keycloak
    keycloak_config = KeycloakConfiguration(
        url="https://sso.your-keycloak.com/auth/",
        realm="<Realm Name>",
        client_id="<Client ID>",
        client_secret="<Client Secret>",
        use_introspection_endpoint=True
    )

Please make sure to understand the consequences before applying this configuration.

Device Authentication
^^^^^^^^^^^^^^^^^^^^^

Documentation will follow soon

Excluding Endpoints
^^^^^^^^^^^^^^^^^^^

Documentation will follow soon

Request Injection
^^^^^^^^^^^^^^^^^

.. note::
   This section contains technical details about the implementation within the library and is not required to use the library. Feel free to skip it.

The decorator used to enforce permissions requires to have access to the Request object, as the middleware stores the user information and compiled permissions there.

FastAPI injects the request to the path function, if the path function declares the request parameter. If its not provided by the user, the request would normally not be passed and would therefore not be available to the decorator.

This would end up in some code like this:

.. code-block:: python

    @app.get("/users/me")
    @require_permission("user:read")
    def read_users_me(request: Request): # pylint: disable=unused-argument
        return {"user": "Hello World"}

Not only would this require unneccessary imports and blow up the path function, it would also raise a warning for an unused variable which then would need to be suppressed.

To avoid this, the decorater uses a somewhat "hacky" way to modify the function signature and include the request parameter. This way, the user does not need to declare the request parameter and the decorator can still access it.

Lateron, before actually calling the path function, the request is removed from :code:`kwargs` again, to avoid an exception being raised for an unexpected argument.

Details can be found in `PEP 362 - Function Signature Object <https://peps.python.org/pep-0362/#signature-object>`_. Consider the following code:

.. code-block:: python

    # Get function signature
    sig = signature(func)

    # Get parameters
    parameters: OrderedDict = sig.parameters
    if "request" in parameters.keys():
        # Request is already present, no need to modify signature
        return wrapper

    # Add request parameter by creating a new parameter list based on the old one
    parameters = [
        Parameter(
            name="request",
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=Parameter.empty,
            annotation=starlette.requests.Request,
        ),
        *parameters.values(),
    ]

    # Create a new signature, as the signature is immutable
    new_sig = sig.replace(parameters=parameters, return_annotation=sig.return_annotation)
    
    # Update the wrapper function signature
    wrapper.__signature__ = new_sig
    return wrapper

The request is still passed to the path function if defined by the user, otherwise its removed before calling the path function.
