Introduction
============

Motivation
^^^^^^^^^^

Using FastAPI and Keycloak quite a lot, and keeping to repeat
myself quite a lot when it comes to authentiating users, I
decided to create this library to help with this.

There is a clear separation between the authentication and
authorization:

- **Authentication** is about verifying the identity of the user
  (who they are). This is done by an authentication backend
  that verifies the users access token obtained from the
  identity provider (Keycloak in this case).
- **Authorization** is about deciding which resources can be
  accessed. This package providers convenience decoraters to
  enforce certain roles or permissions on FastAPI endpoints.

Installation
^^^^^^^^^^^^

Install the package using poetry:

.. code-block:: bash

    poetry add fastapi-keycloak-middleware

or pip:

.. code-block:: bash

    pip install fastapi-keycloak-middleware

Features
^^^^^^^^

The package helps with:

* An easy to use middleware that validates the request for an access token
* Validation can done in one of two ways:
   * Validate locally using the public key obtained from Keycloak
   * Validate using the Keycloak token introspection endpoint
* Using Starlette authentication mechanisms to store both the user object as well as the authorization scopes in the Request object
* Ability to provide custom callback functions to retrieve the user object (e.g. from your database) and to provide an arbitrary mapping to authentication scopes (e.g. roles to permissions)
* A decorator to use previously stored information to enforce certain roles or permissions on FastAPI endpoints
* Convenience dependencies to retrieve the user object or the authorization result after evaluation within the FastAPI endpoint

Acknowledgements
^^^^^^^^^^^^^^^^

This package is heavily inspired by `fastapi-auth-middleware <https://github.com/code-specialist/fastapi-auth-middleware>`_
which provides some of the same functionality but without the direct integration
into Keycloak. Thanks for writing and providing this great piece of software!