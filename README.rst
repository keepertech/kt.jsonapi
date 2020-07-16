==============================
kt.jsonapi -- JSON:API support
==============================

``kt.jsonapi`` supports generation of `JSON:API`_ responses using
adaptation from application objects.

Input validation for `JSON:API`_ is not currently provided, but is
planned for the future.

The current implementation works with the Flask_ web framework.


Release history
---------------

#. Provide ``included`` in response if request includes an ``include``
   query parameter, even if the value is an empty list.  Improves
   conformance with JSON:API 1.1.
   https://github.com/json-api/json-api/issues/1230


1.0.0 (2020-07-09)
~~~~~~~~~~~~~~~~~~

First release, internal to Keeper Technology, LLC.


.. _Flask:
   https://flask.palletsprojects.com/

.. _JSON\:API:
   https://jsonapi.org/
