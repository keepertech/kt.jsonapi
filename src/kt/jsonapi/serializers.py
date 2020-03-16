# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
JSON:API serialization for resources.

The serialization functions accept objects that are adaptable to the
interfaces defined in ``kt.jsonapi.interfaces`` and convert to simple
JSON-friendly Python structures.  Each serializer also requires the
parsed request context; some require additional structures.

These are not public API.

"""

import kt.jsonapi.interfaces


def link(link):
    ob = kt.jsonapi.interfaces.ILink(link)
    # if ob is None and isinstance(link, str):
    #     return link
    meta = dict(ob.meta())
    if meta:
        return dict(
            href=ob.href,
            meta=meta,
        )
    else:
        return ob.href


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


def relationship(context, relationship, relname=None):
    collection = None
    r = dict()
    relone = kt.jsonapi.interfaces.IToOneRelationship(relationship, None)
    if relone is not None:
        relationship = relone
        res = relone.resource()

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

    else:
        relmany = kt.jsonapi.interfaces.IToManyRelationship(relationship, None)
        if relmany is not None:
            relationship = relmany
            if relname:
                r['data'] = []
                collection = kt.jsonapi.interfaces.ICollection(
                    relationship.collection())
                for res in collection.resources():
                    res = kt.jsonapi.interfaces.IResource(res)
                    r['data'].append(dict(
                        type=res.type,
                        id=res.id,
                    ))
                    context.include_relation(relname, res)
            else:
                coll = kt.jsonapi.interfaces.ICollection(relmany.collection())
                it = iter(coll.resources())
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

    d = dict(resource.relationships())
    d = context.select_fields(resource.type, d)
    if d:
        for name, rel in d.items():
            relname = name if context.should_include(name) else None
            d[name] = relationship(context, rel, relname=relname)
        r['relationships'] = d

    return r
