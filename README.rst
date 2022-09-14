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


1.7.0 (2022-09-14)
~~~~~~~~~~~~~~~~~~

#. Drop support for Python 3.6.

#. Update to support Flask 2.2 and newer without deprecation warnings.
   The changes to use ``app.json`` or ``app.json_provider_class``
   instead of ``app.json_encoder`` affect many applications that drive
   their own response generation.


1.6.1 (2022-05-12)
~~~~~~~~~~~~~~~~~~

#. Add missing ``long_description`` package metadata.


1.6.0 (2022-05-03)
~~~~~~~~~~~~~~~~~~

#. First public release of ``kt.jsonapi``.

#. Added support for Python 3.10, 3.11.


1.5.0 (2021-09-20)
~~~~~~~~~~~~~~~~~~

#. Bug fix: The context methods ``created()`` and ``resource()`` could
   serialize the primary data into ``included`` as well as ``data`` if a
   circular relationship including the primary data passed into the call
   was included.

#. Fix tests inherited from the ``resource`` tests to actually invoked
   the ``created`` method when run as part of the tests for ``created``.

#. Add response method ``related()`` to generate a serialized response
   for the target of a relationship.  This is useful with regard to
   mutable to-one relationships because of the constraint that the
   ``related`` `resource link not change because of changes to the
   referenced resource`_.

#. Allow a Flask application to provide specialized context
   implementations that can provide appropriate `JSON:API Object`_
   values.

#. Support serialization of a `JSON:API Object`_ with all responses.

#. Avoid unintended chained exceptions in ``context()`` and
   ``error_context()`` high-level functions.


1.4.0 (2021-05-24)
~~~~~~~~~~~~~~~~~~

#. Support JSON:API 1.1 enhancements to the link & error objects.

#. Support ``include`` and ``fields`` as appropriate for responses where
   the primary data is a relationship.  This reflects an extension of
   the relationship interfaces with the ``name`` attribute, which
   remains optional; if not present, ``include`` and ``fields`` continue
   to generate an error.

#. Include content from relationships which were identified in the
   ``include`` query parameter even if the relationships themselves were
   excluded by a ``fields[...]`` parameter.

#. Update to modern PyPA tooling recommendations.


1.3.0 (2021-03-26)
~~~~~~~~~~~~~~~~~~

#. Serialization of errors via adaptation is supported using a new
   context method.  This includes support for multiple error objects in
   a single response.  This does *not* cause JSON:API errors to be
   returned automatically from response methods on the context, since
   switching from a planned response to an error response should invoke
   content negotiation; this is left to integration layers.

#. Support relationships that cannot be included in composite documents
   using the ``include`` query string parameter.  A request for
   inclusion of resources from a non-includable relationship will cause
   an exception indicating a **400 Bad Request** response will be
   raised.  Otherwise, the relationship will be serialized without a
   ``data`` element; only ``links`` and ``meta`` will be included, as
   appropriate.


1.2.1 (2021-01-12)
~~~~~~~~~~~~~~~~~~

#. Support pagination links of ``None`` for collections and to-many
   relationships.

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

#. Fix generation of links for a relationship to correctly deal with
   collection-oriented query parameters (``filter``, ``page``, ``sort``).

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

#. Provide ``included`` in response if request includes an ``include``
   query parameter, even if the value is an empty list.  Improves
   conformance with JSON:API 1.1.
   https://github.com/json-api/json-api/issues/1230

#. Adapt source object to IResource in relationship implementations.


1.0.0 (2020-07-09)
~~~~~~~~~~~~~~~~~~

First release, internal to Keeper Technology, LLC.


.. _Flask:
   https://flask.palletsprojects.com/

.. _JSON\:API:
   https://jsonapi.org/

.. _JSON:API Object:
   https://jsonapi.org/format/#document-jsonapi-object

.. _resource link not change because of changes to the referenced resource:
   https://jsonapi.org/format/#document-resource-object-related-resource-links
