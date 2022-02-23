:mod:`error` --- Error objects
==============================

.. module:: kt.jsonapi.error
   :synopsis: Classes representing JSON:API errors

Definition of convenient :class:`~kt.jsonapi.interfaces.IError` &
:class:`~kt.jsonapi.interfaces.IErrors` implementations.


Implementations
---------------

.. autoclass:: Error

.. autoclass:: Errors
   :special-members: __getitem__, __iter__, __len__


Adapters
--------

These adapters are provided as a convenience, but are not registered.

.. autofunction:: invalidNameError
.. autofunction:: invalidStructureError
.. autofunction:: queryStringError
