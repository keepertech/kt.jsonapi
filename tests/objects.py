# (c) 2020 - 2021.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Example application objects and adapters for tests.

"""

import uuid

import flask
import zope.interface

import kt.jsonapi.interfaces
import kt.jsonapi.link


@zope.interface.implementer(kt.jsonapi.interfaces.IResource)
class SimpleResource:

    def __init__(self, id=None, type='baggage',
                 attributes={}, meta={}, relationships={}):
        if id is None:
            id = str(uuid.uuid4())
        self.id = id
        self.type = type
        self._attributes = dict(attributes)
        self._meta = meta
        self._relationships = dict(relationships)

    def attributes(self):
        return self._attributes

    def links(self):
        href = '/%s/%s' % (self.type, self.id)
        return dict(self=kt.jsonapi.link.Link(href))

    def meta(self):
        return self._meta

    def relationships(self):
        return self._relationships


@zope.interface.implementer(kt.jsonapi.interfaces.ICollection)
class SimpleCollection:

    ncalls_resources = 0
    ncalls_set_filter = 0
    ncalls_set_pagination = 0
    ncalls_set_sort = 0

    def __init__(self, resources=(), meta={}, links={}):
        self._links = dict(links)
        self._meta = dict(meta)
        self._resources = tuple(resources)

    def links(self):
        if not self._links:
            return dict(self=kt.jsonapi.link.Link(flask.request.path))
        else:
            return self._links

    def meta(self):
        return self._meta

    def resources(self):
        self.ncalls_resources += 1
        return self._resources

    # The optional expanded interfaces just provide additional methods;
    # what they do is implementation dependent; we're simply going to
    # record the parameters and the number of times each is called for
    # testing purposes.
    #
    # This class doesn't declare the corresponding interfaces; we'll add
    # those directly to the implementations in the tests.

    def set_filter(self, filter):
        self.ncalls_set_filter += 1
        self._meta['filter'] = filter

    def set_pagination(self, page):
        self.ncalls_set_pagination += 1
        self._meta['page'] = page

    def set_sort(self, sort):
        self.ncalls_set_sort += 1
        self._meta['sort'] = sort


@zope.interface.implementer(kt.jsonapi.interfaces.IToOneRelationship)
class ToOneRel:

    includable = True

    def __init__(self, related, meta={}, name=None, source=None):
        if related is not None:
            related = kt.jsonapi.interfaces.IResource(related)
        self.name = name
        self.source = source
        self._related = related
        self._meta = meta

    def links(self):
        links = {}
        if self._related is not None:
            rlinks = self._related.links()
            if 'self' in rlinks:
                links['related'] = rlinks['self']
        return links

    def meta(self):
        return self._meta

    def resource(self):
        return self._related


class ToOneAddressableRel(ToOneRel):

    def __init__(self, related, meta={}, link=None, name=None, source=None):
        super(ToOneAddressableRel, self).__init__(related, meta,
                                                  name=name, source=source)
        self._self_link = link

    def links(self):
        links = super(ToOneAddressableRel, self).links()
        if self._self_link is None:
            if self._related is None:
                self._self_link = kt.jsonapi.link.Link(
                    '/mycontext/42/relationships/myrelation',
                    meta=dict(faux=True))
            else:
                self._self_link = kt.jsonapi.link.Link(
                    links['related'].href + '/relationships/myrelation')
        links['self'] = self._self_link
        return links


@zope.interface.implementer(kt.jsonapi.interfaces.IToManyRelationship)
class ToManyRel:

    includable = True

    def __init__(self, collection=None, meta=None,
                 related_link=None, self_link=None, name=None, source=None):
        self.name = name
        self.source = source
        if collection is None:
            collection = SimpleCollection()
        self._collection = collection
        self._meta = meta
        self._related_link = related_link
        self._self_link = self_link

    def links(self):
        links = {}
        if self._related_link is not None:
            links['related'] = self._related_link
        if self._self_link is not None:
            links['self'] = self._self_link
        return links

    def meta(self):
        if self._meta is None:
            return self._collection.meta()
        else:
            return self._meta

    def collection(self):
        return self._collection


class UntypedRel:
    # Show that relationship objects need to be explicity to-one or
    # to-many; anything else is ill-defined.

    includable = True

    def data(self):
        return None

    def links(self):
        return {}

    def meta(self):
        return {}


class IAppObject(zope.interface.Interface):
    """Just a marker."""


@zope.interface.implementer(IAppObject)
class AppObject:

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@zope.interface.implementer(kt.jsonapi.interfaces.IResource)
class AppAdapter:

    type = 'app-object'
    id = '86'

    def __init__(self, context):
        self.ob = context

    def attributes(self):
        return self.ob.__dict__

    def links(self):
        return {'self': kt.jsonapi.link.Link('/foo/86')}

    def meta(self):
        return {}

    def relationships(self):
        return {}
