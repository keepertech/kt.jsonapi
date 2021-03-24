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

#. Support relationships that cannot be included in composite documents
   using the ``include`` query string parameter.  A request for
   inclusion of resources from a non-empty, non-includable relationship
   will cause an exception indicating a **400 Bad Request** response
   will be raised.  If not mentioned in ``include``, the relationship
   will be serialized without a ``data`` element; only ``links`` and
   ``meta`` will be included, as appropriate.
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/-/issues/6


1.2.1 (2021-01-12)
~~~~~~~~~~~~~~~~~~

#. Support pagination links of ``None`` for collections and to-many
   relationships.
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/issues/11

#. Treat an empty ``include`` query parameter as an empty list of
   relationship paths.  This was previously silently treated as an empty
   relationship path, though invalid.
   https://github.com/json-api/json-api/issues/1530


1.2.0 (2021-01-04)
~~~~~~~~~~~~~~~~~~

#. Manage query parameters for top-level **self** and pagination links.
   This can be a significant change for applications that deal with
   query parameters themselves.
   https://github.com/json-api/json-api/issues/1502
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/issues/8

#. Fix generation of links for a relationship to correctly deal with
   collection-oriented query parameters (``filter``, ``page``, ``sort``).
   https://kt-git.keepertech.com/DevTools/kt.jsonapi/issues/10

#. Validate relationship paths passed to the ``include`` query parameter.

#. Change constructor for ``Context`` object to accept both the Flask
   application and request objects, and update call sites to de-proxy
   those before passing them in.  This (slightly) improves the
   resilience of the constructed context to be less dependent on the
   source thread.

#. Change constructor signature for ``Link`` object to accept a ``meta``
   parameter instead of assembling keyword parameters into the
   dictionary for arbitrary metadata.  This will allow additional future
   flexibility for parameters with more specific interpretation.


1.1.0 (2020-10-27)
~~~~~~~~~~~~~~~~~~

#. Added ``created()`` method on the context object, for use in
   returning a response containing a newly created resource.  Similar to
   ``resource()``, it returns a 201 status code and a serialization of
   the created resource.


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
