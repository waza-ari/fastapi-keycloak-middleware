.. FastAPI Keycloak Middleware documentation master file, created by
   sphinx-quickstart on Sat Mar 25 20:24:27 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

FastAPI KeyCloak Middleware
===========================

This package provides a middleware for `FastAPI <http://fastapi.tiangolo.com>`_  that simplifies
integrating with `Keycloak <http://http://keycloak.org>`_ for  
authentication and authorization. It supports OIDC and supports validating access tokens,
reading roles and basic authentication. In addition it provides several decorators and 
dependencies to easily integrate into your FastAPI application.

It relies on the `python-keycloak <http://python-keycloak.readthedocs.io>`_ package, which
is the only dependency outside of the FastAPI ecosystem which would be installed anyway. 
Shoutout to the author of `fastapi-auth-middleware <https://github.com/code-specialist/fastapi-auth-middleware>`_
which served as inspiration for this package and some of its code.

In the future, I plan to add support for fine grained authorization using Keycloak Authorization
services.

.. toctree::
   :maxdepth: 5
   :caption: Contents:

   intro
   usage
   authorization
   advanced_topics
   testing
   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
