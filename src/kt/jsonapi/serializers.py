"""\
JSON:API serialization for resources.

The serialization functions accept objects that are adaptable to the
interfaces defined in ``kt.jsonapi.interfaces`` and convert to simple
JSON-friendly Python structures.  Each serializer also requires the
parsed request context; some require additional structures.

These are not public API.

"""

import werkzeug.exceptions

import kt.jsonapi.interfaces


def link(lynk):
    ob = kt.jsonapi.interfaces.ILink(lynk)
    # if ob is None and isinstance(link, str):
    #     return link
    d = dict(href=ob.href)
    if ob.rel:
        d['rel'] = ob.rel
    if ob.describedby:
        d['describedby'] = link(ob.describedby)
    if ob.title:
        d['title'] = ob.title
    if ob.type is not None:
        d['type'] = ob.type
    hreflang = ob.hreflang
    if hreflang:
        d['hreflang'] = hreflang
    meta = dict(ob.meta())
    if meta:
        d['meta'] = meta
    if len(d) == 1:
        return ob.href
    else:
        return d


def _collection_links(ob):
    links = dict(ob.links())
    for name, val in list(links.items()):
        if val is None and name in ('first', 'next', 'last', 'prev'):
            continue
        links[name] = link(val)
    return links


def _links(ob):
    links = dict(ob.links())
    return {name: link(val)
            for name, val in links.items()}


def error(error):
    r = dict()
    if error.id is not None:
        r['id'] = error.id
    if error.status is not None:
        r['status'] = str(error.status)
    if error.code is not None:
        r['code'] = error.code
    if error.title is not None:
        r['title'] = error.title
    if error.detail is not None:
        r['detail'] = error.detail
    lnks = _links(error)
    if lnks:
        r['links'] = lnks
    meta = error.meta()
    if meta:
        r['meta'] = meta
    src = error.source()
    if src:
        r['source'] = src
    if not r:
        # https://github.com/json-api/json-api/issues/1496
        raise kt.jsonapi.interfaces.InvalidResultStructure('error')
    return r


def relationship(context, relationship, relname=None):
    collection = None
    r = dict()
    relone = kt.jsonapi.interfaces.IToOneRelationship(relationship, None)
    if relone is not None:
        relationship = relone
        res = relone.resource()

        if relationship.includable:
            if res is None:
                r['data'] = None
            else:
                res = kt.jsonapi.interfaces.IResource(res)
                r['data'] = dict(
                    type=res.type,
                    id=res.id,
                )
                if relname:
                    context.include_relation(relname, res)
        elif relname:
            raise werkzeug.exceptions.BadRequest(
                f'requested relationship "{relname}" cannot be included')

    else:
        relmany = kt.jsonapi.interfaces.IToManyRelationship(relationship, None)
        if relmany is not None:
            relationship = relmany
            collection = kt.jsonapi.interfaces.ICollection(
                relationship.collection())

            if relationship.includable and relname:
                r['data'] = []
                for res in collection.resources():
                    res = kt.jsonapi.interfaces.IResource(res)
                    r['data'].append(dict(
                        type=res.type,
                        id=res.id,
                    ))
                    context.include_relation(relname, res)
            elif relname:
                raise werkzeug.exceptions.BadRequest(
                    f'requested relationship "{relname}" cannot be included')
            else:
                it = iter(collection.resources())
                try:
                    res = next(it)
                except StopIteration:
                    # Empty!  Make it easy to discover without another request:
                    r['data'] = []

        else:
            # No idea what this is.
            raise TypeError('relationship value does not provide a concrete'
                            ' relationship type')

    r.update(_relationship_body_except_data(relationship, collection))
    return r


def _relationship_body_except_data(relationship, collection=None):
    r = dict()

    if collection is None:
        d = _links(relationship)
    else:
        d = _collection_links(relationship)
    if d:
        r['links'] = d

    d = dict(relationship.meta())
    if d:
        r['meta'] = d

    return r


def resource(context, resource):
    resource = kt.jsonapi.interfaces.IResource(resource)
    r = dict(
        type=resource.type,
        id=resource.id,
    )

    d = dict(resource.attributes())
    d = context.select_fields(resource.type, d)
    if d:
        r['attributes'] = d

    d = _links(resource)
    if d:
        r['links'] = d

    d = dict(resource.meta())
    if d:
        r['meta'] = d

    rels = dict(resource.relationships())
    d = context.select_fields(resource.type, rels).copy()
    if d:
        for name, rel in d.items():
            relname = name if context.should_include(name) else None
            d[name] = relationship(context, rel, relname=relname)
            # Avoid considering this relationship for inclusion again:
            del rels[name]
        r['relationships'] = d
    for name, rel in rels.items():
        if context.should_include(name):
            relationship(context, rel, relname=name)

    return r
