# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses
#
# All the ValueError exceptions raised here should be something more
# specific that better indicates the source of the problem.

"""\
Top-level API to construct JSON:API responses from application objects.

"""

import json
import urllib.parse

import flask
import werkzeug.exceptions

import kt.jsonapi.interfaces
import kt.jsonapi.serializers


CONTENT_TYPE = 'application/vnd.api+json'
"""Media type associated with JSON:API payloads."""


def _field_ref(names):
    names = list(names)
    parts = [names.pop(0)]
    parts += [f'[{name}]' for name in names]
    return ''.join(parts)


def _check_name(name, key):
    if not name:
        raise kt.jsonapi.interfaces.InvalidQueryKey(
            f'empty names not allowed in query string keys: {key!r}',
            key=key)


def _split_key(key):
    # key should look something like 'name0[name1][name2]';
    # pick it apart into a sequence of names: ['name0', 'name1', 'name2']
    if '[' in key:
        ndx = key.index('[')
        name = key[:ndx]
        rest = key[ndx:]
        _check_name(name, key)
        names = [name]
        while rest:
            if (']' not in rest) or not rest.startswith('['):
                raise kt.jsonapi.interfaces.InvalidQueryKey(
                    f'malformed query string key segment following'
                    f' {_field_ref(names)!r}: {rest!r}',
                    key=key)
            name, rest = rest[1:].split(']', 1)
            _check_name(name, key)
            names.append(name)
        field = names.pop()
        return tuple(names), field
    else:
        return (), key


def _ismap(ob):
    return isinstance(ob, dict)


class Context(object):
    """Request context containing JSON:API-specific information.

    Sub-classes or alternatives may be constructed for request objects
    from different web frameworks; this is built for Flask requests.

    """

    # Needs to deal with fields, include, maybe pagination.

    # JSON:API-defined query parameters, some of which can be 'deep'
    # structures.
    #
    # What a request might reasonably need will generally depend on the
    # method, and we probably want more context when validating values.
    #
    _query_parts = 'fields', 'filter', 'include', 'page', 'sort'

    _field_name = kt.jsonapi.interfaces.MemberName()
    _type_name = kt.jsonapi.interfaces.TypeName()

    def __init__(self, request):
        """Initialize information needed from the request.

        All information is captured from the request up front, instead
        of relying on being able to get it later.  Any errors that can
        be detected while parsing the query string will be raised as
        early as possible.

        """
        # request information
        self.fields = {}
        self.relpaths = set()
        self._parse_query_string(self._extract_query_string(request))

        # response information
        self.included = []
        self._included_idents = set()
        self._json_encoder = flask.current_app.json_encoder
        self._relstack = []

    def _extract_query_string(self, request):
        return request.query_string.decode('utf-8')

    def _parse_query_string(self, query_string):
        input = urllib.parse.parse_qs(query_string, keep_blank_values=True)
        self._query = dict()
        for key, values in input.items():
            topname, _, _ = key.partition('[')
            if topname not in self._query_parts:
                continue
            obnames, field = _split_key(key)

            ob = self._query
            for n, name in enumerate(obnames):
                if name in ob:
                    if not isinstance(ob[name], dict):
                        # Already a non-dict from based on another key; not
                        # allowed.
                        raise kt.jsonapi.interfaces.InvalidQueryKeyUsage(
                            f'{_field_ref(obnames[:n+1])!r} is already a value'
                            f' field, and cannot be used as a container for'
                            f' {key!r}',
                            key=key)
                    ob = ob[name]
                else:
                    ob[name] = dict()
                    ob = ob[name]
            if field in ob and isinstance(ob[field], dict):
                # Already a non-dict from based on another key; not allowed.
                raise kt.jsonapi.interfaces.InvalidQueryKeyUsage(
                    f'{key!r} is already a container, and cannot be used as'
                    f' a value field',
                    key=key)
            if topname in ('filter', 'page', 'sort'):
                values, = values
            ob[field] = values

        # Should validate all type names and field names using the
        # appropriate schema fields.
        if 'fields' in self._query and not _ismap(self._query['fields']):
            raise kt.jsonapi.interfaces.InvalidQueryKeyValue(
                "query string key 'fields' must map type names"
                " to lists of field names",
                key='fields',
                value=self._query['fields'])
        for tname, tfields in self._query.get('fields', {}).items():
            key = f'fields[{tname}]'
            self._type_name.validate(tname)
            # validate type name
            if isinstance(tfields, dict):
                raise kt.jsonapi.interfaces.InvalidQueryKeyValue(
                    f'value for query string key {key!r}'
                    f' must not contain nested containers',
                    key=key,
                    value=tfields)
            if len(tfields) != 1:
                raise kt.jsonapi.interfaces.InvalidQueryKeyUsage(
                    f'query string key {key!r} may have only one value',
                    key=key)
            if tfields[0]:
                tfields = tfields[0].split(',')
                for tfield in tfields:
                    # validate field name
                    self._field_name.validate(tfield)
                self.fields[tname] = set(tfields)
            else:
                self.fields[tname] = set()

        if 'include' in self._query:
            key = 'include'
            if isinstance(self._query['include'], dict):
                raise kt.jsonapi.interfaces.InvalidQueryKeyValue(
                    f'value for query string key {key!r}'
                    f' must not contain nested containers',
                    key=key,
                    value=self._query['include'])
            if len(self._query['include']) != 1:
                raise kt.jsonapi.interfaces.InvalidQueryKeyUsage(
                    f'query string key {key!r} may have only one value',
                    key=key)
            for part in self._query['include'][0].split(','):
                relnames = part.split('.')
                relpath = []
                for relname in relnames:
                    # validate relname
                    relpath.append(relname)
                    self.relpaths.add('.'.join(relpath))

    def select_fields(self, typename, map):
        # Can be used for both attributes, relationships.
        if typename in self.fields:
            selected = self.fields[typename]
            map = {k: map[k] for k in map if k in selected}
        return map

    def should_include(self, relname):
        # Check to see if the relationship relname should be included.
        # Need to track relationship path as we descend.
        relpath = list(self._relstack)
        relpath.append(relname)
        relpath = '.'.join(relpath)
        return relpath in self.relpaths

    def include_relation(self, relname, resource):
        key = resource.type, resource.id
        if key not in self._included_idents:
            relstack = list(self._relstack)
            self._relstack.append(relname)
            try:
                self._included_idents.add(key)
                self.included.append(
                    kt.jsonapi.serializers.resource(self, resource))
            finally:
                self._relstack[:] = relstack

    # Methods to construct response:

    def collection(self, collection, headers=None):
        """Generate response containing a collection as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        """
        collection = kt.jsonapi.interfaces.ICollection(collection)
        self._prepare_collection(collection)

        # Serialize.
        resources = list(kt.jsonapi.interfaces.IResource(resource)
                         for resource in collection.resources())
        for resource in resources:
            key = resource.type, resource.id
            assert key not in self._included_idents
            self._included_idents.add(key)
        data = [kt.jsonapi.serializers.resource(self, resource)
                for resource in resources]
        links = kt.jsonapi.serializers._collection_links(collection)
        meta = dict(collection.meta())
        r = dict(data=data)
        if self.included or self.relpaths:
            r['included'] = self.included
        if meta:
            r['meta'] = meta
        if links:
            r['links'] = links
        return self._response(r, headers=headers)

    def _prepare_collection(self, collection):
        self._collection_prop(
            collection, kt.jsonapi.interfaces.IFilterableCollection,
            'set_filter', 'filter', 'filtering')
        self._collection_prop(
            collection, kt.jsonapi.interfaces.ISortableCollection,
            'set_sort', 'sort', 'sorting')
        self._collection_prop(
            collection, kt.jsonapi.interfaces.IPagableCollection,
            'set_pagination', 'page', 'pagination')

    def _collection_prop(self, collection, iface, method, key, verb):
        if iface.providedBy(collection):
            if key in self._query:
                method = getattr(collection, method)
                method(self._query[key])
        elif key in self._query:
            raise werkzeug.exceptions.BadRequest(
                f'{verb} is not supported by collection')

    def relationship(self, relationship, headers=None):
        """Generate response containing a relationship as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        """
        if self.fields or self.relpaths:
            raise werkzeug.exceptions.BadRequest(
                'cannot specify sparse field sets or relationships'
                ' to include for a relationship')

        rel = kt.jsonapi.interfaces.IToManyRelationship(relationship, None)
        if rel is None:
            # Reject collection parameters; order should match that of
            # _prepare_collection.
            for verb in ('filter', 'sort', 'page'):
                if verb in self._query:
                    raise werkzeug.exceptions.BadRequest(
                        f'{verb} is not supported for to-one relationship')
            body = kt.jsonapi.serializers.relationship(self, relationship)
        else:
            # to-many, so collection parameters are applicable.
            collection = kt.jsonapi.interfaces.ICollection(rel.collection())
            self._prepare_collection(collection)
            resources = list(kt.jsonapi.interfaces.IResource(resource)
                             for resource in collection.resources())
            data = [dict(type=resource.type, id=resource.id)
                    for resource in resources]
            # We're doing this mostly to pick up pagination links:
            body = kt.jsonapi.serializers._relationship_body_except_data(
                rel, collection)
            body['data'] = data
        return self._response(body, headers=headers)

    def resource(self, resource, headers=None):
        """Generate response containing a resource as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        """
        data = kt.jsonapi.serializers.resource(self, resource)
        data = dict(data=data)
        if self.included or self.relpaths:
            data['included'] = self.included
        return self._response(data, headers=headers)

    def created(self, resource, headers=None, location=None):
        """Generate response containing a resource as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        The response will carry a 201 status code to indicate that the
        resource was successfully created.

        """
        data = kt.jsonapi.serializers.resource(self, resource)
        data = dict(data=data)
        if self.included or self.relpaths:
            data['included'] = self.included
        hdrs = flask.app.Headers()
        if headers is not None:
            hdrs.extend(headers)
        if location:
            hdrs['Location'] = location
        return self._response(data, headers=hdrs, status=201)

    def _response(self, body, headers=None, status=200):
        data = json.dumps(body, cls=self._json_encoder).encode('utf-8')
        hdrs = flask.app.Headers()
        if headers is not None:
            hdrs.extend(headers)
        if 'Content-Type' not in hdrs:
            hdrs['Content-Type'] = CONTENT_TYPE
        return flask.make_response(data, status, hdrs)


def context():
    """Get JSON:API context for current Flask request.

    A new context will be created if needed.  At most one context will
    be associated with each request.

    """
    try:
        ctx = flask.g.__jsonapi_context
    except AttributeError:
        ctx = Context(flask.request)
        flask.g.__jsonapi_context = ctx
    return ctx
