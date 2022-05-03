"""\
Interfaces for JSON:API representations of application objects.

"""

import re
import typing

import zope.interface
import zope.interface.common.interfaces
import zope.interface.common.mapping
import zope.interface.common.sequence
import zope.schema
import zope.schema.interfaces


_re_gac = r'[a-zA-Z0-9\u0080-\uffff]'
_re_memch = r'[-a-zA-Z0-9\u0080-\uffff_ ]'

_re_member_name = f'{_re_gac}({_re_memch}*{_re_gac})?$'
_rx_member_name = re.compile(_re_member_name.replace(' ', ''))


# --------------------
# Exception interfaces


class IQueryStringException(zope.interface.common.interfaces.IValueError):
    """Interface for QueryStringException instances."""

    key = zope.schema.TextLine(
        title='Key',
        description='Name of key in query string',
        required=True,
    )


class IInvalidNameException(zope.interface.common.interfaces.IException):
    """Interface for the Invalid* exceptions."""

    field = zope.schema.Object(
        description='Field which failed validation',
        schema=zope.schema.interfaces.IField,
        required=True,
    )

    value = zope.interface.Attribute("Value determined to be invalid")


class IInvalidResultStructure(zope.interface.common.interfaces.IValueError):
    """Interface for InvalidResultStructure instances."""

    kind = zope.schema.TextLine(
        description=('Name of the structure as defined in the'
                     ' JSON:API specification'),
        required=True,
    )


# ----------
# Exceptions


@zope.interface.implementer(IInvalidNameException)
class _InvalidName(zope.schema.interfaces.ValidationError):
    """Name is invalid according to JSON:API."""


class InvalidMemberName(_InvalidName):
    """Member name is invalid according to JSON:API."""


class InvalidRelationshipPath(_InvalidName):
    """Relationship path includes invalid member name according to JSON:API.
    """


class InvalidTypeName(_InvalidName):
    """Type name is invalid according to JSON:API."""


@zope.interface.implementer(IQueryStringException)
class QueryStringException(ValueError):
    """Something is wrong with the format or content of the query string."""

    def __init__(self, message, key):
        """Initialize with an error message and the key from query string."""
        super(QueryStringException, self).__init__(message)
        self.key = key


class InvalidQueryKey(QueryStringException):
    """A key in the query string is malformed."""


class InvalidQueryKeyUsage(QueryStringException):
    """A key in the query string is used inconsistently."""


class InvalidQueryKeyValue(QueryStringException):
    """A key in the query string has an unsupported value."""

    def __init__(self, message, key, value):
        """Initialize with message, key and value from query string."""
        super(InvalidQueryKeyValue, self).__init__(message, key)
        self.value = value


@zope.interface.implementer(IInvalidResultStructure)
class InvalidResultStructure(ValueError):
    """Serialization resulted in an invalid structure."""

    def __init__(self, kind):
        """Construct exception for a specific *kind* of structure.

        *kind* should be a term defined in the JSON:API specification.

        """
        super(InvalidResultStructure, self).__init__(kind)
        self.kind = kind

    def __str__(self):
        return f'serialization generated invalid structure for {self.kind}'


# -----------------
# Field definitions


class _Name(zope.schema.TextLine):

    def __init__(self, *args, **kwargs):
        # The constructor for zope.interface.Element uses __name__ for
        # __doc__, and sets __name__ to None, if there's a space in
        # __name__.  Since our field names are generated based on user
        # input, this is wrong behavior for us, so work around it.
        name = kwargs.pop('__name__', None)
        kwargs['__name__'] = 'xxx'
        super(_Name, self).__init__(*args, **kwargs)
        self.__name__ = name

    def constraint(self, value):
        if _rx_member_name.match(value) is None:
            raise self._exception().with_field_and_value(self, value)
        else:
            return True


class MemberName(_Name):
    """Member name, as defined by JSON:API.

    Allowed member names are `constrained by the specification
    <https://jsonapi.org/format/#document-member-names>`__.
    This definition applies to the names of attributes and relationships.

    Raises :exc:`InvalidMemberName` when constraints are not satisfied.

    """

    _exception = InvalidMemberName


class RelationshipPath(_Name):
    """Dotted sequence of member names, as defined by JSON:API.

    Allowed member names are `constrained by the specification
    <https://jsonapi.org/format/#document-member-names>`__.
    This definition applies to the names of attributes and relationships.

    Raises :exc:`InvalidRelationshipPath` when constraints are not satisfied.

    """

    _exception = InvalidRelationshipPath

    def constraint(self, value):
        try:
            for part in value.split('.'):
                super(RelationshipPath, self).constraint(part)
        except InvalidRelationshipPath as e:
            e.value = value
            raise
        else:
            return True


class TypeName(_Name):
    """Type name, as defined by JSON:API.

    Allowed type names are `constrained by the specification
    <https://jsonapi.org/format/#document-resource-object-identification>`__
    in the same way as member names.

    Raises :exc:`InvalidTypeName` when constraints are not satisfied.

    """

    _exception = InvalidTypeName


class URL(zope.schema.TextLine):

    def __init__(self, title=None, description=None, min_length=None,
                 **kwargs):
        kwargs.update(
            title=(title or 'URL'),
            description=(description or 'Absolute or relative URL'),
            min_length=(min_length or 1),
        )
        super(URL, self).__init__(**kwargs)


# ---------------------------------------------
# Interfaces used when everything is going well


class IFieldMapping(zope.interface.common.mapping.IEnumerableMapping):
    """Mapping from field names to JSON-encodable values.

    Keys are only strings that conform to the JSON:API field name
    constraints.

    """


class IRelationships(zope.interface.common.mapping.IEnumerableMapping):
    """Mapping from field names to IRelationship instances.

    Keys are only strings that conform to the JSON:API field name
    constraints.

    """


class IMetadataProvider(zope.interface.Interface):

    def meta() -> IFieldMapping:
        """Retrieve a mapping containing non-standard, named metadata fields.

        The mapping may be empty.

        """


class ILink(IMetadataProvider):

    href = URL(required=True)

    rel = zope.schema.ASCIILine(
        description='The :rfc:`8288` relationship type of the link.',
        min_length=1,
        required=False,
        missing_value=None,
    )

    describedby = zope.schema.Object(
        description='''
            Link to a description document describing the link target.
            This is usualy a specification such as OpenAPI, JSON Schema,
            or XML Schema.
        ''',
        # NB: This gets fixed up below; we can't refer to ILink yet.
        schema=IMetadataProvider,
        required=False,
        missing_value=None,
    )

    title = zope.schema.TextLine(
        description='''
            Human-facing title for the link, possibly suitable as a
            menu entry.  This is not necessarily the title of the
            linked document.
        ''',
        min_length=1,
        required=False,
        missing_value=None,
    )

    type = zope.schema.ASCIILine(
        description='Media type of the document referenced by *href*.',
        min_length=3,
        required=False,
        missing_value=None,
    )

    hreflang = zope.interface.Attribute('hreflang', '''
        String or sequence of strings specifying languages the target
        document is available in.  Each entry must conform to
        :rfc:`5646`.  May be `None`.
    ''')


ILink.get('describedby').schema = ILink


class ILinksProvider(zope.interface.Interface):

    def links() -> IFieldMapping:
        """Retrieve a mapping containing standard, named links.

        The mapping may be empty.

        Consumers are not required to support link names that are not
        defined in the JSON:API specification.

        """


class IResourceIdentifer(IMetadataProvider):

    id = zope.schema.Text(
        title='Identifier',
        description=('Identifier to distinguish resource from'
                     ' from others of the same type'),
        required=True,
        readonly=True,
    )

    type = MemberName(
        title='Type',
        description='JSON:API resource type identifier',
        required=True,
        readonly=True,
    )


class IResource(IResourceIdentifer, ILinksProvider):

    def attributes() -> IFieldMapping:
        """Return mapping of attribute names to values."""

    def relationships() -> IRelationships:
        """Return mapping of relationship names to relationship objects."""


class ICollection(ILinksProvider, IMetadataProvider):

    def resources():
        """Return sequence of resources of collection.

        This method will only be called once, and the return value will
        only be interated over once.

        """


class IFilterableCollection(ICollection):

    def set_filter(filter):
        """Apply filtering parameters from the request.

        If the specific filtering parameters provided are not
        supported, an appropriate ``BadRequest`` exception must be
        raised.

        This will not be invoked if no filtering parameters were
        supplied; the collection should behave as if no filtering were
        requested.

        If filtering is requested, this will be called *before* the
        :meth:`~kt.jsonapi.interfaces.ICollection.resources` method is
        called.

        Filtering parameters will be applied before sorting parameters
        (if applicable) or pagination parameters (if applicable).

        """


class ISortableCollection(ICollection):

    def set_sort(sort):
        """Apply sorting parameters from the request.

        If the specific sorting parameters provided are not supported,
        an appropriate ``BadRequest`` exception must be raised.

        This will not be invoked if no sorting parameters were supplied;
        the collection should behave as if no sorting were requested.

        If sorting is requested, this will be called *before* the
        :meth:`~kt.jsonapi.interfaces.ICollection.resources` method is
        called.

        Sorting parameters will be applied after filtering parameters
        (if applicable) and before pagination (if applicable).

        """


class IPagableCollection(ICollection):

    def set_pagination(page):
        """Apply pagination parameters from the request.

        This is expected to affect the results returned by the
        :meth:`~ICollection.resources` and :meth:`~ICollection.links`
        methods.

        If the specific pagination parameters provided are not
        supported, an appropriate ``BadRequest`` exception must be
        raised.

        This will not be invoked if no pagination parameters were
        supplied; the collection should behave as if default pagination
        were requested.

        If pagination parameters are provided, this will be called
        *before* the :meth:`~kt.jsonapi.interfaces.ICollection.resources`
        method is called.

        Pagination parameters will be applied after filtering parameters
        (if applicable) and sorting parameters (if applicable).

        """


class IRelationshipBase(ILinksProvider, IMetadataProvider):

    includable = zope.schema.Bool(
        title='Includable',
        description="""
            Indicates whether relationship can be included via ``include``
            query string parameter.

            If a non-includable relationship is requested for inclusion
            via ``include``, an exception triggering a **400 Bad Request**
            response will be raised during serialization.

            When a non-includable relationship is serialized, no ``data``
            member will be generated.  For to-one relationships, the'
            resource will not be retrieved from the relationship, and for
            to-many relationships, the collection's ``resources()`` method
            will not be called.

        """,
        required=True,
        readonly=True,
    )

    name = MemberName(
        title='Name',
        description="""
            Field name of the relationship.

            .. versionadded:: 1.4.0
               *name* added to relationship interfaces.  Relationships
               without a value for this attribute cannot be returned as
               primary data when ``fields`` or ``include`` are specified
               in the request.
        """,
        missing_value=None,
        # Can't require this, since we're adding this in a later version.
        required=False,
        readonly=True,
    )

    source = zope.schema.Object(
        title='Source',
        description='Resource containing this relationship.',
        schema=IResource,
        # Can't require this, since we're adding this in a later version.
        required=False,
        readonly=True,
    )


class IToOneRelationship(IRelationshipBase):

    def resource() -> typing.Optional[IResource]:
        """Return resource referenced by to-one relationship, or None."""


class IToManyRelationship(IRelationshipBase):

    def collection() -> ICollection:
        """Return collection of resources of to-many relationship.

        The collection may be filterable, sortable, or pagable, as
        appropriate.  Those additional aspects will only be invoked if
        the relationship is rendered as the primary data in a response.

        """


class IError(ILinksProvider, IMetadataProvider):
    """Presentation of a single error.

    See `Error Objects <https://jsonapi.org/format/#error-objects>`__
    for discussion on the specific information that each field or method
    result represents.

    """

    id = zope.schema.Text(
        title='Identifier',
        description='Identifier for this particular instance of a problem',
        required=False,
        missing_value=None,
    )

    status = zope.schema.Int(
        title='Status code',
        description='HTTP status code',
        min=400,
        max=599,
        required=False,
        missing_value=None,
    )

    code = zope.schema.TextLine(
        title='Code',
        description='Error code identifying the specific application error',
        required=False,
        missing_value=None,
    )

    title = zope.schema.TextLine(
        title='Title',
        description='Human-facing title describing the application error',
        required=False,
        missing_value=None,
    )

    detail = zope.schema.Text(
        title='Detailed description',
        description='Human-facing description of this instance of the problem',
        required=False,
        missing_value=None,
    )

    def source() -> IFieldMapping:
        """Returns mapping containing references to the source of the error.

        The mapping may be empty.

        """


class IErrors(zope.interface.common.sequence.IMinimalSequence):
    """Interface representing a collection of `IError` instances.

    When generating a JSON:API response from an exception, the exception
    will be adapted to this interface if possible.  On success, each
    entry in the ``errors`` property in the generated response will
    correspond to an entry in this sequence.

    This sequence cannot be empty.

    """
