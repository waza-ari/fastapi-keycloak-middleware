[![Documentation Status](https://readthedocs.org/projects/fastapi-keycloak-middleware/badge/?version=latest)](https://fastapi-keycloak-middleware.readthedocs.io/en/latest/?badge=latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)
![GitHub issues](https://img.shields.io/github/issues/waza-ari/fastapi-keycloak-middleware)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/waza-ari/fastapi-keycloak-middleware)
![GitHub top language](https://img.shields.io/github/languages/top/waza-ari/fastapi-keycloak-middleware)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/waza-ari/fastapi-keycloak-middleware/development.svg)](https://results.pre-commit.ci/latest/github/waza-ari/fastapi-keycloak-middleware/development)


# FastAPI Keycloak Middleware

**Full documentation** is [available at Read The Docs](https://fastapi-keycloak-middleware.readthedocs.io/en/latest/)

This package provides a middleware for [FastAPI](http://fastapi.tiangolo.com)  that
simplifies integrating with [Keycloak](http://keycloak.org) for
authentication and authorization. It supports OIDC and supports validating access
tokens, reading roles and basic authentication. In addition it provides several
decorators and dependencies to easily integrate into your FastAPI application.

It relies on the [python-keycloak](http://python-keycloak.readthedocs.io) package,
which is the only dependency outside of the FastAPI ecosystem which would be installed
anyway. Shoutout to the author of [fastapi-auth-middleware](https://github.com/code-specialist/fastapi-auth-middleware)
which served as inspiration for this package and some of its code.

In the future, I plan to add support for fine grained authorization using Keycloak
Authorization services.

## Motivation

Using FastAPI and Keycloak quite a lot, and keeping to repeat myself quite a lot when
it comes to authentiating users, I decided to create this library to help with this.

There is a clear separation between the authentication and authorization:

- **Authentication** is about verifying the identity of the user
  (who they are). This is done by an authentication backend
  that verifies the users access token obtained from the
  identity provider (Keycloak in this case).
- **Authorization** is about deciding which resources can be
  accessed. This package providers convenience decoraters to
  enforce certain roles or permissions on FastAPI endpoints.

## Installation

Install the package using poetry:

```bash
poetry add fastapi-keycloak-middleware
```

or `pip`:

```bash
pip install fastapi-keycloak-middleware
```

## Features

The package helps with:

* An easy to use middleware that validates the request for an access token
* Validation can done in one of two ways:
   * Validate locally using the public key obtained from Keycloak
   * Validate using the Keycloak token introspection endpoint
* Using Starlette authentication mechanisms to store both the user object as well as the authorization scopes in the Request object
* Ability to provide custom callback functions to retrieve the user object (e.g. from your database) and to provide an arbitrary mapping to authentication scopes (e.g. roles to permissions)
* A decorator to use previously stored information to enforce certain roles or permissions on FastAPI endpoints
* Convenience dependencies to retrieve the user object or the authorization result after evaluation within the FastAPI endpoint

## Acknowledgements

This package is heavily inspired by [fastapi-auth-middleware](https://github.com/code-specialist/fastapi-auth-middleware)
which provides some of the same functionality but without the direct integration
into Keycloak. Thanks for writing and providing this great piece of software!

## Contributing

The client is written in pure Python.
Any changes or pull requests are more than welcome, but please adhere to the code style.

Ruff is used both for code formatting and linting. Before committing, please run the following command to ensure
that your code is properly formatted:

```bash
ruff check .
ruff format .
```

A pre-commit hook configuration is supplied as part of the project.

## Development

This project is using [Act](https://github.com/nektos/act) to handle local development tasks. It is used
to work locally and also to test Github actions before deploying them.
