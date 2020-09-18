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


1.0.1 (2020-09-18)
~~~~~~~~~~~~~~~~~~

#. Support explicit request to receive no fields by resource type.  This
   reflects a recent clarification added to the JSON:API specification.
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/issues/7

#. Provide ``included`` in response if request includes an ``include``
   query parameter, even if the value is an empty list.  Improves
   conformance with JSON:API 1.1.
   https://github.com/json-api/json-api/issues/1230

#. Adapt source object to IResource in relationship implementations.
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/issues/9


1.0.0 (2020-07-09)
~~~~~~~~~~~~~~~~~~

First release, internal to Keeper Technology, LLC.


.. _Flask:
   https://flask.palletsprojects.com/

.. _JSON\:API:
   https://jsonapi.org/
