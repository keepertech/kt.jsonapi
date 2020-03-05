:mod:`interfaces` --- Interface definitions
===========================================

.. module:: kt.jsonapi.interfaces
   :synopsis: Interface definitions for adaptation


Exceptions
----------

.. autoexception:: InvalidQueryKey
.. autoexception:: InvalidQueryKeyUsage
.. autoexception:: InvalidQueryKeyValue


Interfaces
----------

.. autointerface:: IFieldMapping
.. autointerface:: ILink
.. autointerface:: ICollection
.. autointerface:: IFilterableCollection
     :members: set_filter
.. autointerface:: ISortableCollection
     :members: set_sort
.. autointerface:: IPagableCollection
     :members: set_pagination
.. autointerface:: IResource
.. autointerface:: IToOneRelationship
.. autointerface:: IToManyRelationship
