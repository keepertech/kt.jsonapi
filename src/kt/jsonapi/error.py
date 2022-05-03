"""\
Definition of convenient :class:`~kt.jsonapi.interfaces.IError` &
:class:`~kt.jsonapi.interfaces.IErrors` implementations.

"""

import typing

import zope.component
import zope.interface
import zope.interface.common.sequence

import kt.jsonapi.interfaces
import kt.jsonapi.link


@zope.interface.implementer(kt.jsonapi.interfaces.IError)
class Error:
    """Representation of a single error."""

    def __init__(self,
                 id: typing.Optional[str] = None,
                 status: typing.Optional[int] = None,
                 code: typing.Optional[str] = None,
                 title: typing.Optional[str] = None,
                 detail: typing.Optional[str] = None,
                 about: typing.Optional[str] = None,
                 type: typing.Optional[str] = None,
                 pointer: typing.Optional[str] = None,
                 parameter: typing.Optional[str] = None,
                 header: typing.Optional[str] = None,
                 meta: typing.Optional[dict] = None):
        """Initialize error structure.

        :param id: Identifier of specific instance of problem.
        :param status: HTTP response status code.
        :param code: Application-specific code for the kind of error.
        :param title:
            Human-oriented high-level description of the kind of error.
            This should not be instance specific.
        :param detail:
            Human-oriented description of the problem; may contain
            instance-specific details.
        :param about:
            Link to human-oriented description of the specific problem;
            may contain instance-specific details.  The response to
            requesting the link may perform content negotiation to
            return a document in an appropriate format and language for
            presentation.  Used to populate the ``links`` object in the
            error object.
        :param type:
            Link to human-oriented description of the general problem;
            must not contain instance-specific details.  The response to
            requesting the link may perform content negotiation to
            return a document in an appropriate format and language for
            presentation.  Used to populate the ``links`` object in the
            error object.
        :param pointer:
            JSON Pointer referring to part of a request document which
            caused the error.
            Used to populate the ``source`` object in the error object.
        :param parameter:
            Name of a query string parameter that triggered the error.
            Used to populate the ``source`` object in the error object.
        :param header:
            Name of a request header that triggered the error.
            Used to populate the ``source`` object in the error object.
        :param meta:
            Mapping providing non-standard fields of additional data
            that should be serialized as the ``meta`` member of the error.

        """
        self.id = id
        self.status = status
        self.code = code
        self.title = title
        self.detail = detail
        self._about = about
        self._type = type
        self._pointer = pointer
        self._parameter = parameter
        self._header = header
        self._meta = meta or {}

    def _build_link(self, value):
        if isinstance(value, str):
            value = kt.jsonapi.link.Link(value)
        return value

    def links(self):
        """Return links for the error.

        This uses the *about* and *type* parameters to the constructor,
        if provided.

        """
        links = {}
        if self._about is not None:
            links['about'] = self._about = self._build_link(self._about)
        if self._type is not None:
            links['type'] = self._type = self._build_link(self._type)
        return links

    def meta(self):
        """Return metadata for this error.

        This returns a dictionary with the content passed to the
        constructor as *meta*, if any.  Otherwise, returns an empty
        dictionary.

        """
        return dict(self._meta)

    def source(self):
        """Return error source information.

        This uses the *header*, *pointer* and *parameter* arguments to
        the constructor to identify the error source.

        """
        d = {}
        if self._pointer:
            d['pointer'] = self._pointer
        if self._parameter:
            d['parameter'] = self._parameter
        if self._header:
            d['header'] = self._header
        return d


@zope.component.adapter(kt.jsonapi.interfaces.IInvalidNameException)
@zope.interface.implementer(kt.jsonapi.interfaces.IError)
def invalidNameError(exc):
    """Adapt invalid name exception to an
    :class:`~kt.jsonapi.interfaces.IError`.

    :param exc: Exception object to adapt.

    """
    return Error(
        status=400,
        title=exc.__doc__.strip() or None,
        detail=str(exc),
        parameter=exc.field.__name__,
        meta=dict(invalid_value=exc.value),
    )


@zope.component.adapter(kt.jsonapi.interfaces.IInvalidResultStructure)
@zope.interface.implementer(kt.jsonapi.interfaces.IError)
def invalidStructureError(exc):
    """Adapt invalid result structure exception to an
    :class:`~kt.jsonapi.interfaces.IError`.

    :param exc: Exception object to adapt.

    """
    return Error(
        status=500,
        title=exc.__doc__.strip() or None,
        detail=str(exc),
        meta=dict(structure_type=exc.kind),
    )


@zope.component.adapter(kt.jsonapi.interfaces.IQueryStringException)
@zope.interface.implementer(kt.jsonapi.interfaces.IError)
def queryStringError(exc):
    """Adapt query string exception to an
    :class:`~kt.jsonapi.interfaces.IError`.

    :param exc: Exception object to adapt.

    """
    return Error(
        status=400,
        title=exc.__doc__.strip() or None,
        detail=str(exc),
        parameter=exc.key,
    )


@zope.interface.implementer(kt.jsonapi.interfaces.IErrors,
                            zope.interface.common.sequence.IFiniteSequence)
class Errors:
    """Representation of a sequence of errors."""

    def __init__(self, errors):
        """Initialize from an iterable providing objects adaptable to
        :class:`~kt.jsonapi.interfaces.IError`.

        The iterable must provide at least one error object.

        """
        errors = tuple(errors)
        if not errors:
            raise ValueError('sequence of errors cannot be empty')
        self._errors = errors

    def __getitem__(self, index: int):
        """Retrieve specific error from the sequence."""
        return self._errors[index]

    def __iter__(self):
        """Iterate over the errors, adapting them to
        :class:`~kt.jsonapi.interfaces.IError`.
        """
        yield from self._errors

    def __len__(self) -> int:
        """Return the number of errors."""
        return len(self._errors)
