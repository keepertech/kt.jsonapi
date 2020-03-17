# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Implementations of relationships that can be re-used.

The terminology used here treats relationships as directional links (or
edges) in a graph.  These links have a *source* resource and either an
(optional) *target* resource, or a *collection* of target resources,
using the JSON:API notions of collection and resource.

For to-one relationships, the target must be an object that can be
adapted to :class:`~kt.jsonapi.interfaces.IResource`, or ``None``.

For to-many relationships, the collection of target resources must be
specified as an object adaptable to an
:class:`~kt.jsonapi.interfaces.ICollection`, but the collection can be
empty.

JSON:API supports the notion that a relationship may be directly
addressable by URL, but does not require that all resources be so.  If
they are, they advertise the URL as their ``self`` link, and the URL
must support the HTTP GET method with a JSON:API response.  Both
relationship classes defined here accept an *addressable* parameter that
causes an appropriate link to be generated using the URL patterns used
in the JSON:API specification.

"""

import typing

import zope.interface

import kt.jsonapi.interfaces


class RelationshipBase:

    def __init__(self, source, target, name, addressable):
        if addressable and not name:
            raise ValueError('addressable relationships must have a name')
        self.source = source
        self.target = target
        self.name = name
        self.addressable = addressable

    def meta(self):
        """Minimal implementation returning empty relationship metadata.

        If specific metadata should be provided for a relationship,
        derive a new relationship class and override this method.

        """
        return {}


@zope.interface.implementer(kt.jsonapi.interfaces.IToOneRelationship)
class ToOneRelationship(RelationshipBase):
    """Implementation for a to-one relationship."""

    def __init__(self,
                 source: kt.jsonapi.interfaces.IResource,
                 target: typing.Optional[kt.jsonapi.interfaces.IResource],
                 name: typing.Optional[str] = None,
                 addressable: bool = False,
                 indirect: bool = False):
        """Initialize relationship.

        :param source:  Resource object which owns the relationship.
        :param target:  Resource object related to the source; may be ``None``.
        :param name:
            Name of the relationship.
            Required if either ``indirect`` or ``addressable`` is true.
        :param addressable:
            Indicates whether the relationship itself is addressable via URL.
        :param indirect:
            Indicates whether the relationship generates links to the target
            directly, or uses links relative to the source which are resolved
            separately.

        If *indirect* is true, a ``related`` link will be generated
        based on the ``self`` link for the *source* resource and the
        *name* for the relationship.  The application must arrange for
        an appropriate response to requests for this link.

        """
        if indirect and not name:
            raise ValueError('indirect relationships must have a name')
        super(ToOneRelationship, self).__init__(source, target, name,
                                                addressable)
        self.indirect = indirect

    def links(self):
        """Generate links appropriate for this relationship.

        If this relationship is addressable, a ``self`` link will be
        included.

        If this relationship is indirect or non-empty, a ``related``
        link will be included.

        """
        source_href = self.source.links()['self'].href
        links = {}
        if self.indirect:
            links['related'] = kt.jsonapi.link.Link(
                f'{source_href}/{self.name}')
        elif self.target is not None:
            related = kt.jsonapi.interfaces.IResource(self.target)
            links['related'] = related.links()['self']
        if self.addressable:
            links['self'] = kt.jsonapi.link.Link(
                f'{source_href}/relationships/{self.name}')
        return links

    def resource(self):
        return self.target


@zope.interface.implementer(kt.jsonapi.interfaces.IToManyRelationship)
class ToManyRelationship(RelationshipBase):
    """Implementation for a to-many relationship."""

    def __init__(self,
                 source: kt.jsonapi.interfaces.IResource,
                 collection: kt.jsonapi.interfaces.ICollection,
                 name: typing.Optional[str] = None,
                 addressable: bool = False):
        """Initialize relationship.

        :param source:  Resource object which owns the relationship.
        :param collection:  Collection of related resources.
        :param name:
            Name of the relationship.
            Required if either ``indirect`` or ``addressable`` is true.
        :param addressable:
            Indicates whether the relationship itself is addressable via URL.
        """
        target = kt.jsonapi.interfaces.ICollection(collection)
        super(ToManyRelationship, self).__init__(source, target, name,
                                                 addressable)

    def collection(self):
        return self.target

    def links(self):
        """Generate links appropriate for this relationship.

        The ``related`` link will always be generated as the ``self``
        link of the relationship's collection.

        If this relationship is addressable, a ``self`` link will be
        included.

        """
        links = dict(
            related=self.target.links()['self'],
        )
        if self.addressable:
            source_href = self.source.links()['self'].href
            links['self'] = kt.jsonapi.link.Link(
                f'{source_href}/relationships/{self.name}')
        return links
