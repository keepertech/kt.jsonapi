"""\
Top-level API to construct JSON:API responses from application objects.

"""

# All the ValueError exceptions raised here should be something more
# specific that better indicates the source of the problem.

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
    #
    # key should look something like 'name0[name1][name2]';
    # pick it apart into a sequence of names and a final field:
    #   ==> ('name0', 'name1'), 'name2'
    #
    # A simple key that contains no [...] parts generates only the
    # final field and an empty prefix sequence:
    #   ==> (), 'name0'
    #
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


class QueryParameter:

    __slots__ = 'key', 'value', 'aspect'

    def __init__(self, key, value, aspect=None):
        super(QueryParameter, self).__init__()
        self.key = key
        self.value = value
        self.aspect = aspect


class _BaseContext:

    def __init__(self, app, request):
        """Initialize information needed from the request.

        All information is captured from the request up front, instead
        of relying on being able to get it later.

        """
        self._json_encoder = app.json_encoder

    def error(self, error, headers=None):
        """Generate error response from exception.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        """
        seq = kt.jsonapi.interfaces.IErrors(error, None)
        if seq is None:
            ierr = kt.jsonapi.interfaces.IError(error)
            seq = (ierr,)
        else:
            seq = tuple(kt.jsonapi.interfaces.IError(error)
                        for error in seq)
        body = dict(errors=[kt.jsonapi.serializers.error(err)
                            for err in seq])
        statuses = set(err.status for err in seq if err.status)
        if len(statuses) == 1:
            # All the same, just use it:
            status = statuses.pop()
        elif not statuses:
            # Nothing specified, so the situation is bad:
            status = 500
        else:
            statuses = sorted(statuses)
            if statuses[-1] >= 500:
                status = 500
            else:
                status = 400
        return self._response(body, headers=headers, status=status)

    def jsonapi(self):
        """Return a `JSON:API Object`_ that should be included in responses.

        This may be invoked for either a successful or error response.

        The default implementation returns an empty dictionary, which
        will be dropped in serialization since it doesn't contribute any
        information to the response.

        .. _JSON:API Object:
           https://jsonapi.org/format/#document-jsonapi-object
        """
        return {}

    def _response(self, body, headers=None, status=200):
        jsonapi = self.jsonapi()
        if jsonapi:
            jsonapi = dict(jsonapi)
            if 'meta' in jsonapi and not jsonapi['meta']:
                del jsonapi['meta']
            body['jsonapi'] = jsonapi
        data = json.dumps(body, cls=self._json_encoder).encode('utf-8')
        hdrs = flask.app.Headers()
        if headers is not None:
            hdrs.extend(headers)
        if 'Content-Type' not in hdrs:
            hdrs['Content-Type'] = CONTENT_TYPE
        return flask.make_response(data, status, hdrs)


class Context(_BaseContext):
    """Request context containing JSON:API-specific information.

    Sub-classes or alternatives may be constructed for request objects
    from different web frameworks; this is built for Flask requests.

    """

    # JSON:API-defined query parameters, some of which can be 'deep'
    # structures.
    #
    _query_parts = 'fields', 'filter', 'include', 'page', 'sort'

    _relationship_path = kt.jsonapi.interfaces.RelationshipPath(
        __name__='include')

    def __init__(self, app, request):
        """Initialize information needed from the request.

        All information is captured from the request up front, instead
        of relying on being able to get it later.  Any errors that can
        be detected while parsing the query string will be raised as
        early as possible.

        """
        super(Context, self).__init__(app, request)
        # request information
        self.fields = {}
        self.relpaths = set()
        self._parse_query_string(self._extract_query_string(request))

        # response information
        self.included = []
        self._included_idents = set()
        self._relstack = []

    def _extract_query_string(self, request):
        return request.query_string.decode('utf-8')

    def _parse_query_string(self, query_string):
        qparams = []
        self._query = dict()
        for key, value in urllib.parse.parse_qsl(query_string,
                                                 keep_blank_values=True):
            topname, _, _ = key.partition('[')
            aspect = topname if topname in self._query_parts else None
            qparams.append(QueryParameter(key, value, aspect))
            if not aspect:
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
            if field in ob:
                raise kt.jsonapi.interfaces.InvalidQueryKeyUsage(
                    f'query string key {key!r} may have only one value',
                    key=key)
            ob[field] = value

        self._qparams = tuple(qparams)

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
            kt.jsonapi.interfaces.TypeName(__name__=key).validate(tname)
            # validate type name
            if isinstance(tfields, dict):
                raise kt.jsonapi.interfaces.InvalidQueryKeyValue(
                    f'value for query string key {key!r}'
                    f' must not contain nested containers',
                    key=key,
                    value=tfields)
            if tfields:
                tfields = tfields.split(',')
                field = kt.jsonapi.interfaces.MemberName(__name__=key)
                for ndx, tfield in enumerate(tfields):
                    # validate field name
                    field.validate(tfield)
                self.fields[tname] = set(tfields)
            else:
                self.fields[tname] = set()

        if 'include' in self._query:
            key = 'include'
            include = self._query[key]
            if isinstance(include, dict):
                raise kt.jsonapi.interfaces.InvalidQueryKeyValue(
                    f'value for query string key {key!r}'
                    f' must not contain nested containers',
                    key=key,
                    value=include)
            includes = include.split(',') if include else []
            for part in includes:
                self._relationship_path.validate(part)
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

        The **links** member of the response payload will include a
        **self** link based on the **self** link for the collection, with
        query parameters copied from the request.  Pagination links
        provided by the :meth:`~kt.jsonapi.interfaces.ILinksProvider.links`
        method for the collection will be augmented based on the query
        parameters of the request with the incoming pagination
        parameters stripped out.

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
        if 'include' in self._query:
            r['included'] = self.included
        if meta:
            r['meta'] = meta
        if links:
            self._apply_query_params(links)
            r['links'] = links
        return self._response(r, headers=headers)

    def _apply_query_params(self, links):
        for lname in ('self', 'first', 'next', 'prev', 'last'):
            if lname not in links:
                continue
            link = links[lname]
            if link is None:
                continue
            if lname == 'self':
                items = self._query_params()
            else:
                items = self._query_params(excluding={'page'})
            if not items:
                continue
            items = [f'{qp.key}={qp.value}' for qp in items]
            items = '&'.join(items)
            if isinstance(link, str):
                # just a string, not an object
                qp = '&' if '?' in link else '?'
                links[lname] = f'{link}{qp}{items}'
            else:
                link = links[lname]['href']
                qp = '&' if '?' in link else '?'
                links[lname]['href'] = f'{link}{qp}{items}'

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
                qdata = self._query[key]
                method(qdata)
        elif key in self._query:
            raise werkzeug.exceptions.BadRequest(
                f'{verb} is not supported by collection')

    def _disallow_collection_params(self, what):
        for verb in ('filter', 'sort', 'page'):
            if verb in self._query:
                raise werkzeug.exceptions.BadRequest(
                    f'{verb} is not supported for {what}')

    def _query_params(self, excluding=frozenset()):
        return [qparam for qparam in self._qparams
                if qparam.aspect not in excluding]

    def _check_rel_fields_include(self, rel):
        name = getattr(rel, 'name', None)
        if name:
            if self.fields and 'include' not in self._query:
                raise werkzeug.exceptions.BadRequest(
                    'cannot specify sparse field sets for a relationship'
                    ' without using include to request resources')
            prefix = name + '.'
            badpaths = []
            for relpath in self.relpaths:
                if relpath == name or relpath.startswith(prefix):
                    continue
                badpaths.append(relpath)
            if badpaths:
                badpaths.sort()
                exc = werkzeug.exceptions.BadRequest(
                    f'cannot include relationship paths that do not start'
                    f' with "{name}"')
                exc.disallowed_relationship_paths = badpaths
                raise exc
        elif self.fields or 'include' in self._query:
            raise werkzeug.exceptions.BadRequest(
                'cannot specify sparse field sets or relationships'
                ' to include for a relationship')

    def related(self, relationship, headers=None):
        """Generate response containing a relationship target as primary data.

        Unlike the :meth:`resource` method, the response may include
        ``null`` as the primary data if *relationship* is an empty
        to-one relationship.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        The **links** member of the response payload will include
        augmented **self** and pagination links as appropriate, as
        provided by the
        :meth:`~kt.jsonapi.interfaces.ILinksProvider.links` method for
        the relationship, with query parameters copied from the request.
        Pagination links will be augmented based on the query parameters
        from the request with the incoming pagination parameters
        stripped out.

        """
        rel = kt.jsonapi.interfaces.IToManyRelationship(relationship, None)
        if rel is not None:
            return self.collection(rel.collection(), headers=headers)

        # Reject collection parameters; order should match that of
        # _prepare_collection.
        self._disallow_collection_params('resource')
        rel = kt.jsonapi.interfaces.IToOneRelationship(relationship)
        resource = rel.resource()
        if resource is not None:
            resource = kt.jsonapi.interfaces.IResource(resource)
            key = resource.type, resource.id
            self._included_idents.add(key)
            resource = kt.jsonapi.serializers.resource(self, resource)
        body = dict(
            data=resource,
        )
        name = getattr(rel, 'name', None)
        source = getattr(rel, 'source', None)
        if name and source is not None:
            source = kt.jsonapi.interfaces.IResource(source)
            source_links = source.links()
            self_link = f'{source_links["self"].href}/{name}'
            body['links'] = dict(self=self_link)
            self._apply_query_params(body['links'])
        if 'include' in self._query:
            body['included'] = self.included

        return self._response(body, headers=headers)

    def relationship(self, relationship, headers=None):
        """Generate response containing a relationship as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        The **links** member of the response payload will include
        augmented **self** and pagination links, as provided by the
        :meth:`~kt.jsonapi.interfaces.ILinksProvider.links` method for
        the relation, with query parameters copied from the request.
        Pagination links will be augmented based on the query parameters
        from the request with the incoming pagination parameters stripped
        out.

        If *relationship* has a value for the ``name`` attribute and is
        includable, the ``fields`` and ``include`` query parameters can
        be applied.  ``fields`` is only allowed if ``include`` is also
        provided.  If ``include`` specifies relationship paths that do
        not start with the name of *relationship*, a 400 response will
        be triggered.  If *relationship* is not includable, a 400
        response will be triggered.

        If there is no ``name`` value, the presence of a ``fields`` or
        ``include`` parameter will trigger a 400 response.

        .. versionchanged:: 1.4.0
           Prior versions always triggered a 400 response if ``fields``
           or ``include`` were present in the query string.

        """
        rel = kt.jsonapi.interfaces.IToManyRelationship(relationship, None)
        if rel is None:
            # Reject collection parameters; order should match that of
            # _prepare_collection.
            self._disallow_collection_params('to-one relationship')
            rel = kt.jsonapi.interfaces.IToOneRelationship(relationship, None)
            self._check_rel_fields_include(rel)
            name = getattr(rel, 'name', None)
            name = name if (name and self.should_include(name)) else None
            body = kt.jsonapi.serializers.relationship(self, rel,
                                                       relname=name)
        else:
            self._check_rel_fields_include(rel)
            name = getattr(rel, 'name', None)
            name = name if (name and self.should_include(name)) else None
            # to-many, so collection parameters are applicable.
            collection = kt.jsonapi.interfaces.ICollection(rel.collection())
            self._prepare_collection(collection)
            resources = list(kt.jsonapi.interfaces.IResource(resource)
                             for resource in collection.resources())
            data = []
            for resource in resources:
                data.append(dict(type=resource.type, id=resource.id))
                if name:
                    self.include_relation(name, resource)
            # We're doing this mostly to pick up pagination links:
            body = dict(
                kt.jsonapi.serializers._relationship_body_except_data(
                    rel, collection),
                data=data,
            )
        if body.get('links'):
            self._apply_query_params(body['links'])
        if 'include' in self._query:
            body['included'] = self.included

        return self._response(body, headers=headers)

    def resource(self, resource, headers=None):
        """Generate response containing a resource as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        The **links** member of the response payload will include a
        **self** link based on the **self** link for the resource, with
        query parameters copied from the request.

        """
        self._disallow_collection_params('resource')
        resource = kt.jsonapi.interfaces.IResource(resource)
        key = resource.type, resource.id
        self._included_idents.add(key)
        data = kt.jsonapi.serializers.resource(self, resource)
        link = self._resource_self_link(data)
        data = dict(data=data)
        if link:
            data['links'] = dict(self=link)
            self._apply_query_params(data['links'])
        if 'include' in self._query:
            data['included'] = self.included
        return self._response(data, headers=headers)

    def created(self, resource, headers=None, location=None):
        """Generate response containing a resource as primary data.

        If *headers* is given and non-``None``, it must be be mapping of
        additional headers that should be returned in the request.  If a
        **Content-Type** header is provided, it will be used instead of
        the default value for JSON:API responses.

        The **links** member of the response payload will include a
        **self** link based on the **self** link for the resource, with
        query parameters copied from the request.

        The response will carry a 201 status code to indicate that the
        resource was successfully created.

        """
        self._disallow_collection_params('resource')
        resource = kt.jsonapi.interfaces.IResource(resource)
        key = resource.type, resource.id
        self._included_idents.add(key)
        data = kt.jsonapi.serializers.resource(self, resource)
        link = self._resource_self_link(data)
        data = dict(data=data)
        if link:
            data['links'] = dict(self=link)
            self._apply_query_params(data['links'])
        if 'include' in self._query:
            data['included'] = self.included
        hdrs = flask.app.Headers()
        if headers is not None:
            hdrs.extend(headers)
        if location:
            hdrs['Location'] = location
        return self._response(data, headers=hdrs, status=201)

    def _resource_self_link(self, data):
        link = None
        if 'links' in data and 'self' in data['links']:
            link = data['links']['self']
            if isinstance(link, dict):
                link = link['href']
        return link


class ErrorContext(_BaseContext):
    """Request context for JSON:API responses.

    This context is suitable for handling errors being returned to a
    client, but not for general JSON:API response serialization.  No
    parsing of the query string is performed, allowing JSON:API error
    responses to be provided even from endpoints that take incompatible
    query string parameters.

    """


def context():
    """Get JSON:API context for current Flask request.

    A new context will be created if needed.  At most one context will
    be associated with each request.

    If the ``'KT_JSONAPI_CONTEXT_REGULAR'`` setting is specified in
    ``flask.current_app.config``, it should be a factory for a context
    object.  This will normally be derived from :class:`Context`.

    """
    return __get_context(factory=Context, factory_name='REGULAR')


def error_context():
    """Get JSON:API context for current Flask request, suitable for error
    serialization.

    A new context will be created if needed, but no new query string
    parsing will be performed.  At most one context will be associated
    with each request.

    Only the :meth:`~kt.jsonapi.api.Context.error` method should be
    invoked on the returned context.

    If the ``'KT_JSONAPI_CONTEXT_ERROR'`` setting is specified in
    ``flask.current_app.config``, it should be a factory for a context
    object.  This will normally be derived from :class:`ErrorContext`.

    """
    ctx = __get_context(factory=ErrorContext, factory_name='ERROR')
    if ctx.__class__ is Context:
        ctx.__class__ = ErrorContext
    return ctx


def __get_context(factory, factory_name):
    try:
        return flask.g.__jsonapi_context
    except AttributeError:
        # pass & fall through to avoid the confusing chained exception
        # when things go wrong building the context based on the
        # request.
        pass
    config = flask.current_app.config
    factory = config.get(f'KT_JSONAPI_CONTEXT_{factory_name}', factory)
    ctx = factory(flask.current_app._get_current_object(),
                  flask.request._get_current_object())
    flask.g.__jsonapi_context = ctx
    return ctx
