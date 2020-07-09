kt.jsonapi
==========

.. toctree::
    :maxdepth: 5

    introduction
    api
    interfaces
    link
    relation


``kt.jsonapi`` supports generation of `JSON:API`_ responses using
adaptation from application objects.

Input validation for `JSON:API`_ is not currently provided, but is
planned for the future.

The current implementation works with the Flask_ web framework.


JSON:API features supported
---------------------------

Compound documents
~~~~~~~~~~~~~~~~~~

`Inclusion of Related Resources`_ describes use of the ``include`` query
parameter to drive the inclusion of additional related resources in a
response.  This query string is handled directly when responses are
generated using the :meth:`~kt.jsonapi.api.Context.collection` and
:meth:`~kt.jsonapi.api.Context.resource` methods (the only times
``include`` makes sense).


Sparse Fieldsets
~~~~~~~~~~~~~~~~

`Sparse Fieldsets`_ defines a way for clients to limit the fields
returned for particular types of resources using query parameters of the
form ``fields[TYPENAME]``, where ``TYPENAME`` is replaced by a type
identifier.  No additional support from the application is required.


Collection handling
~~~~~~~~~~~~~~~~~~~

Collections of resources may be sortable, filterable, and pagable,
though they are not required to be any of these.  Each requires
additional support from the application.  Collection objects should
additionally implement
:class:`~kt.jsonapi.interfaces.IFilterableCollection`,
:class:`~kt.jsonapi.interfaces.ISortableCollection`, and
:class:`~kt.jsonapi.interfaces.IPagableCollection` as appropriate.


.. _Flask:
   https://flask.palletsprojects.com/

.. _Inclusion of Related Resources:
   https://jsonapi.org/format/#fetching-includes

.. _JSON\:API:
   https://jsonapi.org/

.. _Sparse Fieldsets:
   https://jsonapi.org/format/#fetching-sparse-fieldsets
