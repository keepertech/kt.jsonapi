:mod:`interfaces` --- Interface definitions
===========================================

.. module:: kt.jsonapi.interfaces
   :synopsis: Interface definitions for adaptation


Exceptions
----------

.. autoexception:: InvalidMemberName
.. autoexception:: InvalidTypeName
.. autoexception:: InvalidRelationshipPath

.. autoexception:: InvalidQueryKey
    :no-special-members:

    .. automethod:: __init__

    .. attribute:: key
        :type: str

        Key from query string that cannot be interpreted.
        This will be a key that presents a leading segment with one of
        the names defined in the JSON:API specification.

.. autoexception:: InvalidQueryKeyUsage
    :no-special-members:

    .. automethod:: __init__

    .. attribute:: key
        :type: str

        Key from query string that cannot be interpreted.
        This will be a key that presents a leading segment with one of
        the names defined in the JSON:API specification.

.. autoexception:: InvalidQueryKeyValue
    :no-special-members:

    .. automethod:: __init__

    .. attribute:: key
        :type: str

        Key from query string that cannot be interpreted.
        This will be a key that presents a leading segment with one of
        the names defined in the JSON:API specification.

    .. attribute:: value

        Value acquired from the query string before interpretation was
        attempted.


Fields
------

These are :mod:`zope.schema` field types that can be used to describe
JSON:API concepts.

.. autoclass:: MemberName
.. autoclass:: TypeName
.. autoclass:: RelationshipPath
.. autoclass:: URL
    :no-special-members:


Interfaces
----------

.. autointerface:: IFieldMapping
.. autointerface:: IMetadataProvider
.. autointerface:: ILink
.. autointerface:: ILinksProvider
.. autointerface:: ICollection
.. autointerface:: IFilterableCollection
     :members: set_filter
.. autointerface:: ISortableCollection
     :members: set_sort
.. autointerface:: IPagableCollection
     :members: set_pagination
.. autointerface:: IResourceIdentifer
.. autointerface:: IResource
.. autointerface:: IRelationshipBase
.. autointerface:: IToOneRelationship
.. autointerface:: IToManyRelationship
