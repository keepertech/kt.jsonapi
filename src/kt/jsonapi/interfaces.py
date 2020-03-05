# (c) 2019 - 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Interfaces for JSON:API representations of application objects.

"""

import re
import typing

import zope.interface
import zope.interface.common.mapping
import zope.schema
import zope.schema.interfaces


_re_gac = r'[a-zA-Z0-9\u0080-\uffff]'
_re_memch = r'[-a-zA-Z0-9\u0080-\uffff_ ]'

_re_member_name = f'{_re_gac}({_re_memch}*{_re_gac})?$'
_rx_member_name = re.compile(_re_member_name.replace(' ', ''))


class _InvalidName(zope.schema.interfaces.ValidationError):
    """Name is invalid according to JSON:API."""


class InvalidMemberName(_InvalidName):
    """Member name is invalid according to JSON:API."""


class InvalidTypeName(_InvalidName):
    """Type name is invalid according to JSON:API."""


class QueryStringException(ValueError):
    """Something is wrong with the format or content of the query string."""

    def __init__(self, message, key):
        """Initialize with an error message and the key from query string."""
        super(InvalidQueryKey, self).__init__(message)
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


class _Name(zope.schema.TextLine):

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
    )

    type = MemberName(
        title='Type',
        description='JSON:API resource type identifier',
        required=True,
    )


class IResource(IResourceIdentifer, ILinksProvider, IMetadataProvider):

    def attributes() -> IFieldMapping:
        """Return mapping of attribute names to values."""

    def links():
        """Return mapping of link names to link objects."""

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
        ``resources`` method is called.

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
        ``resources`` method is called.

        Sorting parameters will be applied after filtering parameters
        (if applicable) and before pagination (if applicable).

        """


class IPagableCollection(ICollection):

    def set_pagination(page):
        """Apply pagination parameters from the request.

        This is expected to affect the results returned by the
        ``resources`` and ``links`` methods.

        If the specific pagination parameters provided are not
        supported, an appropriate ``BadRequest`` exception must be
        raised.

        This will not be invoked if no pagination parameters were
        supplied; the collection should behave as if default pagination
        were requested.

        If pagination parameters are provided, this will be called
        *before* the ``resources`` method is called.

        Pagination parameters will be applied after filtering parameters
        (if applicable) and sorting parameters (if applicable).

        """


class IToOneRelationship(ILinksProvider, IMetadataProvider):

    def resource() -> typing.Optional[IResource]:
        """Return resource referenced by to-one relationship, or None."""


class IToManyRelationship(ILinksProvider, IMetadataProvider):

    def collection() -> ICollection:
        """Return collection of resources of to-many relationship.

        The collection may be filterable, sortable, or pagable, as
        appropriate.  Those additional aspects will only be invoked if
        the relationship is rendered as the primary data in a response.

        """
