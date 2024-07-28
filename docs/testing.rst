Testing with this library
=========================

When testing your FastAPI application, the default tests will likely fail due to this middleware enforcing authentication.
There are two main methods to test your application when using this middleware, one by simply providing valid access tokens and one by mocking the authentication.
Mocking the authentication is the preferred approach as it allows independent testing of the middleware and the application.
Note that you can still validate permissions if setup correctly.

Prerequisites
-------------

This example is based on pytest, but can be adapted to other testing frameworks. Some dependencies are required to run the tests:

.. code-block:: bash

    poetry add --group dev pytest mock pytest-mock

Mocking the authentication
--------------------------

When not using authorization, you can simply mock the authentication middleware to not apply the middleware in the first place.
To still use users and/or authorization, you need a different way how to pass users to the FastAPI path functions.
Assuming you use a custom user mapper in your application, you can override the dependency to return a user object from your database.

This scenario describes one option of using headers to pass the user information to the FastAPI path functions.
Passing an `X-User` header would tell the overriden dependency which user to inject:

.. code-block:: python

    # It is important that you import your own get_user dependency (when using a custom user mapper)
    # in order to be able to override it. If you use the built-in one, import that one instead.
    from your-library import get_user
    # or
    from fastapi_keycloak_middleware import get_user

    async def mocked_get_user(request: Request):
        """
        This function can be used as FastAPI dependency to easily retrieve the user object from DB
        """
        user = request.headers.get("X-User", "test_user_1")
        # Use whatever method you typically to fetch the user object
        return crud.user.get_by_username(sessionmanager.get_session(), user)

    @pytest.fixture(scope="session")
    def app(session_mocker):

        # Mock auth middleware, effectively remove it
        session_mocker.patch("fastapi_keycloak_middleware.setup_keycloak_middleware")

        # Its important to import the app after the middleware has been mocked
        from backend.main import app as backend_app

        # Override the get_user dependency with our mock method above
        backend_app.dependency_overrides[get_user] = mocked_get_user

        yield backend_app

This code cannot be copied as is, you need to adapt it by either importing the correct ::code:`get_user` method to override
and by implementing your own logic to fetch the user object from the database. With this setup, you can now test your application
and specify the user to be used in the test by setting the `X-User` header:

.. code-block:: python

    # Use default user1, do not specify anything
    def test_with_default_user(app):
        client = TestClient(app)
        response = client.get("/api/v1/your-endpoint")

    # Use specific user for all requests in this test
    def test_with_specific_user(app: FastAPI):
        client = TestClient(app, headers={"X-User": "your-other-user"})
        response = client.get("/api/v1/your-endpoint")

    # Set user on a per request basis
    def test_with_specific_user_on_request(app):
        client = TestClient(app)
        response = client.get("/api/v1/your-endpoint", headers={"X-User": "test_user_2"})

Mocking authorization
---------------------

When also using the authorization features of this library, the process needs to be extended to make sure
the permissions are correctly passed as well and you are able to test your authorization logic.

There are many methods how to implement this, all of them have in common that you need to override the
`get_auth` dependency to return the permissions for the user you want to test with. The example below
sets default roles based on the user, and introduces another header `X-Roles` that can be used to extend
the permissions of a given user on a test-by-test basis. You can implement your own logic there as well,
or rely on database queries to fetch the permissions, if you store your RBAC information in a database.

.. code-block:: python

   async def mocked_get_auth(request: Request):
        user = request.headers.get("X-User", "test_user_1")

        # Set default roles based on the user
        if user.startswith("test_user_admin"):
            roles = ["Admin", "User"]
        elif user.startswith("test_user_guest"):
            roles = ["Guest"]
        elif user.startswith("test_user_"):
            roles = ["User"]
        else:
            roles = [user]

        # Add additional roles if requested
        requested_roles = request.headers.get("X-Roles", "")
        if requested_roles:
            roles += requested_roles.split(",")

        # Optionally, if you normally use an auth_mapper, you can apply it now
        # roles = auth_mapper(roles)
        # or if using async:
        # roles = await auth_mapper(roles)
        return roles

    @pytest.fixture(scope="session")
    def app(session_mocker):

        # Mock auth middleware, effectively remove it
        session_mocker.patch("fastapi_keycloak_middleware.setup_keycloak_middleware")

        # Its important to import the app after the middleware has been mocked
        from backend.main import app as backend_app

        # Override the get_user dependency with our mock method above
        backend_app.dependency_overrides[get_user] = mocked_get_user
        backend_app.dependency_overrides[get_auth] = mocked_get_auth

        yield backend_app

With this setup, you can now test your application and specify the user to be used in the test by setting the `X-User` header
and the roles by setting the `X-Roles` header:

.. code-block:: python

    # Use default user1 with User role, do not specify anything
    def test_with_default_user(app):
        client = TestClient(app)
        response = client.get("/api/v1/your-endpoint")

    # Set user and roles on a per request basis
    def test_with_specific_user_and_roles_on_request(app):
        client = TestClient(app)
        response = client.get("/api/v1/your-endpoint", headers={"X-User": "test_user_2", "X-Roles": "Admin"})
