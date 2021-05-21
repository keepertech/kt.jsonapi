# (c) 2020 - 2021.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Tests for kt.jsonapi.api.Context response methods.

"""

import uuid

import flask_restful
import werkzeug.exceptions
import zope.interface

import kt.jsonapi.api
import kt.jsonapi.error
import kt.jsonapi.interfaces
import kt.jsonapi.link
import kt.jsonapi.serializers
import tests.objects
import tests.test_relation
import tests.utils


@zope.interface.implementer(kt.jsonapi.interfaces.IPagableCollection)
class SimplePagableCollection(tests.objects.SimpleCollection):

    def links(self):
        return dict(
            super(SimplePagableCollection, self).links(),
            next=None,
            prev=None,
        )


def create_collection(test, *ifaces):
    test.r1 = tests.objects.SimpleResource(attributes=dict(simple=True))
    test.r2 = tests.objects.SimpleResource(attributes=dict(simple=False),
                                           meta=dict(last=True))
    test.collection = tests.objects.SimpleCollection([test.r1, test.r2])
    for iface in ifaces:
        zope.interface.alsoProvides(test.collection, iface)


class ErrorResponseTestCase(tests.utils.JSONAPITestCase):

    def setUp(self):
        super(ErrorResponseTestCase, self).setUp()
        self.headers = None

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.error(self.error,
                                          headers=self.headers)

        self.api.add_resource(Render, '/')

    def test_minimal_jsonapi_error(self):
        self.error = kt.jsonapi.error.Error(status=400)

        resp = self.http_get('/', status=self.error.status)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error['status'], '400')
        # This should be the only field, since that's all we defined.
        self.assertEqual(list(error), ['status'])

    def test_maximal_jsonapi_error(self):
        eid = str(uuid.uuid4())
        about_link = (f'https://api.example.com/error/dont-touch-this'
                      f'?report={eid}')
        type_link = 'https://api.example.com/error/dont-touch-this'
        self.error = kt.jsonapi.error.Error(
            id=eid,
            status=403,
            code='dont-touch-this',
            title='Do Not Touch This',
            detail="You don't have permission to touch this.",
            about=about_link,
            type=type_link,
            parameter='this',
        )

        resp = self.http_get('/?this=that', status=self.error.status)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error['code'], self.error.code)
        self.assertEqual(error['detail'], self.error.detail)
        self.assertEqual(error['id'], eid)
        self.assertEqual(error['links'], dict(about=about_link,
                                              type=type_link))
        self.assertEqual(error['source'], dict(parameter='this'))
        self.assertEqual(error['status'], '403')
        self.assertEqual(error['title'], self.error.title)

    def test_jsonapi_error_without_status(self):
        self.error = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            pointer='/data/meta',
        )

        resp = self.http_get('/', status=500)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 1)
        error, = errors
        self.assertEqual(error['id'], self.error.id)
        self.assertEqual(error['source'], dict(pointer='/data/meta'))

    def test_jsonapi_error_with_interesting_link(self):
        eid = str(uuid.uuid4())
        about_link = (f'https://api.example.com/error/dont-touch-this'
                      f'?report={eid}')
        type_link = 'https://api.example.com/error/dont-touch-this'
        self.error = kt.jsonapi.error.Error(
            id=eid,
            status=400,
            about=kt.jsonapi.link.Link(href=about_link,
                                       meta=dict(alternate='just-dont')),
            type=kt.jsonapi.link.Link(href=type_link,
                                      meta=dict(pity='fool')),
            meta=dict(noisy=True),
            header='X-Pity-The-Fool',
        )

        resp = self.http_get('/', status=self.error.status)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 1)
        error = errors[0]
        self.assertEqual(error['id'], eid)
        self.assertEqual(error['links'],
                         dict(
                             about=dict(
                                 href=about_link,
                                 meta=dict(alternate='just-dont'),
                             ),
                             type=dict(
                                 href=type_link,
                                 meta=dict(pity='fool'),
                             ),
                         ))
        self.assertEqual(error['meta'], dict(noisy=True))
        self.assertEqual(error['source'], dict(header='X-Pity-The-Fool'))
        self.assertEqual(error['status'], '400')

    def test_multiple_jsonapi_errors_same_status(self):
        e0 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=403,
            code='dont-touch-this-0',
        )
        e1 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=e0.status,
            code='dont-touch-this-1',
        )
        self.error = kt.jsonapi.error.Errors([e0, e1])

        # Expect the status from the individual errors since they're all
        # the same:
        resp = self.http_get('/?this=that', status=e0.status)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 2)
        err0, err1 = errors
        self.assertEqual(err0['code'], e0.code)
        self.assertEqual(err0['id'], e0.id)
        self.assertEqual(err0['status'], '403')
        self.assertEqual(err1['code'], e1.code)
        self.assertEqual(err1['id'], e1.id)
        self.assertEqual(err1['status'], '403')

    def test_multiple_jsonapi_errors_mixed_errors(self):
        e0 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=501,
            code='cant-find-this-0',
        )
        e1 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=402,
            code='pay-your-bill',
        )
        self.error = kt.jsonapi.error.Errors([e0, e1])

        # Multiple statuses with any >= 500 generate a general 500:
        resp = self.http_get('/?this=that', status=500)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 2)
        err0, err1 = errors
        self.assertEqual(err0['code'], e0.code)
        self.assertEqual(err0['id'], e0.id)
        self.assertEqual(err0['status'], '501')
        self.assertEqual(err1['code'], e1.code)
        self.assertEqual(err1['id'], e1.id)
        self.assertEqual(err1['status'], '402')

    def test_multiple_jsonapi_errors_mixed_client_errors(self):
        e0 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=401,
            code='dont-touch-this-0',
        )
        e1 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=403,
            code='dont-touch-this-1',
        )
        self.error = kt.jsonapi.error.Errors([e0, e1])

        # Multiple statuses all < 500 generate a general 400:
        resp = self.http_get('/?this=that', status=400)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 2)
        err0, err1 = errors
        self.assertEqual(err0['code'], e0.code)
        self.assertEqual(err0['id'], e0.id)
        self.assertEqual(err0['status'], '401')
        self.assertEqual(err1['code'], e1.code)
        self.assertEqual(err1['id'], e1.id)
        self.assertEqual(err1['status'], '403')

    def test_multiple_jsonapi_errors_mixed_server_errors(self):
        e0 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=501,
            code='cant-find-this-0',
        )
        e1 = kt.jsonapi.error.Error(
            id=str(uuid.uuid4()),
            status=502,
            code='cant-talk-to-this',
        )
        self.error = kt.jsonapi.error.Errors([e0, e1])

        # Multiple statuses with any >= 500 generate a general 500:
        resp = self.http_get('/?this=that', status=500)

        content = resp.json
        errors = content['errors']
        self.assertNotIn('data', content)
        self.assertNotIn('included', content)
        self.assertEqual(len(errors), 2)
        err0, err1 = errors
        self.assertEqual(err0['code'], e0.code)
        self.assertEqual(err0['id'], e0.id)
        self.assertEqual(err0['status'], '501')
        self.assertEqual(err1['code'], e1.code)
        self.assertEqual(err1['id'], e1.id)
        self.assertEqual(err1['status'], '502')


class RelationshipResponseTestCase(tests.utils.JSONAPITestCase):

    def setUp(self):
        super(RelationshipResponseTestCase, self).setUp()
        self.headers = None

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.relationship(self.relation,
                                                 headers=self.headers)

        self.api.add_resource(Render, '/')

    def test_to_one_relation_with_filter(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/?filter=something', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('filter is not supported', message)
        self.assertIn('for to-one relationship', message)

    def test_to_one_relation_with_sort(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/?sort=somefield', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('sort is not supported', message)
        self.assertIn('for to-one relationship', message)

    def test_to_one_relation_with_page(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/?page[start]=0&page[limit]=10', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('page is not supported', message)
        self.assertIn('for to-one relationship', message)

    def test_named_relation_with_fields(self):
        self.relation = tests.objects.ToOneRel(None)
        self.relation.name = 'magical'

        resp = self.http_get('/?fields[baggage]=abc,def', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('cannot specify sparse field sets', message)
        self.assertIn('for a relationship', message)
        self.assertIn('without using include', message)

    def test_named_relation_with_disallowed_include(self):
        self.relation = tests.objects.ToOneRel(None)
        self.relation.name = 'magical'

        resp = self.http_get(
            '/?include=magical.comics,muggle.comics', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('cannot include relationship paths that', message)
        self.assertIn('do not start with "magical"', message)

    def test_named_relation_with_allowed_include(self):
        self.relation = tests.objects.ToOneRel(None)
        self.relation.name = 'magical'

        resp = self.http_get('/?include=magical.comics')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected = dict(
            data=None,
            included=[],
        )
        self.assertEqual(resp.get_json(), expected)

    def test_named_to_many_relation_with_allowed_include_included(self):
        comic0 = tests.objects.SimpleResource(
            type='comic', attributes=dict(funny=True))
        comic1 = tests.objects.SimpleResource(
            type='comic', attributes=dict(funny=False))
        self.relation = tests.objects.ToManyRel(
            collection=tests.objects.SimpleCollection(
                resources=[comic0, comic1],
            ),
        )
        self.relation.name = 'comics'

        resp = self.http_get('/?include=comics')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        comic0_expected = dict(
            id=comic0.id,
            type=comic0.type,
            attributes=dict(funny=True),
            links=dict(self=f'/{comic0.type}/{comic0.id}'),
        )
        comic1_expected = dict(
            id=comic1.id,
            type=comic1.type,
            attributes=dict(funny=False),
            links=dict(self=f'/{comic1.type}/{comic1.id}'),
        )
        payload = resp.get_json()
        self.assertEqual(payload['data'],
                         [dict(id=comic0.id, type=comic0.type),
                          dict(id=comic1.id, type=comic1.type)])
        self.assertIn(comic0_expected, payload['included'])
        self.assertIn(comic1_expected, payload['included'])
        self.assertEqual(len(payload['included']), 2)
        self.assertEqual(len(payload), 2)

    def test_named_to_one_relation_with_allowed_include_included(self):
        comic0 = tests.objects.SimpleResource(
            type='comic', attributes=dict(funny=True))
        comic1 = tests.objects.SimpleResource(
            type='comic', attributes=dict(funny=False))
        related = tests.objects.SimpleResource(
            attributes=dict(scale=42),
            relationships=dict(
                comics=tests.objects.ToManyRel(
                    collection=tests.objects.SimpleCollection(
                        resources=[comic0, comic1],
                    ),
                ),
            ),
        )
        self.relation = tests.objects.ToOneRel(related)
        self.relation.name = 'magical'

        resp = self.http_get('/?include=magical.comics')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        comic0_expected = dict(
            id=comic0.id,
            type=comic0.type,
            attributes=dict(funny=True),
            links=dict(self=f'/{comic0.type}/{comic0.id}'),
        )
        comic1_expected = dict(
            id=comic1.id,
            type=comic1.type,
            attributes=dict(funny=False),
            links=dict(self=f'/{comic1.type}/{comic1.id}'),
        )
        related_expected = dict(
            id=related.id,
            type=related.type,
            attributes=dict(scale=42),
            links=dict(self=f'/{related.type}/{related.id}'),
            relationships=dict(
                comics=dict(
                    data=[
                        dict(id=comic0.id, type=comic0.type),
                        dict(id=comic1.id, type=comic1.type),
                    ],
                ),
            ),
        )
        payload = resp.get_json()
        self.assertEqual(payload['data'],
                         dict(id=related.id, type=related.type))
        self.assertEqual(payload['links'],
                         dict(related=f'/{related.type}/{related.id}'))
        self.assertIn(comic0_expected, payload['included'])
        self.assertIn(comic1_expected, payload['included'])
        self.assertIn(related_expected, payload['included'])
        self.assertEqual(len(payload['included']), 3)
        self.assertEqual(len(payload), 3)

    def test_named_non_includable_relation_with_allowed_include(self):
        related = tests.objects.SimpleResource(
            attributes=dict(scale=42),
        )
        self.relation = tests.objects.ToOneRel(related)
        self.relation.includable = False
        self.relation.name = 'magical'

        resp = self.http_get('/?include=magical', status=400)
        self.assertEqual(resp.headers['Content-Type'],
                         'application/json')
        payload = resp.get_json()
        message = payload['message']
        self.assertEqual(
            message,
            'requested relationship "magical" cannot be included')

    def test_unnamed_relation_with_fields(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/?fields[baggage]=abc,def', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('cannot specify sparse field sets', message)
        self.assertIn('for a relationship', message)

    def test_unnamed_relation_with_include(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/?include=abc,def.ghi', status=400)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('cannot specify sparse field sets', message)
        self.assertIn('or relationships to include', message)
        self.assertIn('for a relationship', message)

    def test_empty_to_one_relation(self):
        self.relation = tests.objects.ToOneRel(None)

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(data, dict(data=None))

    def test_passing_headers_through(self):
        self.relation = tests.objects.ToOneAddressableRel(None)
        header_value = 'some-value; charset="us-ascii"'
        self.headers = {'X-Test-Header': header_value}

        resp = self.http_get('/')
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], 'application/vnd.api+json')
        self.assertEqual(hdrs['x-test-header'], header_value)

    def test_provided_content_type_overrides(self):
        self.relation = tests.objects.ToOneAddressableRel(None)
        content_type = 'text/annoying; charset="shift-jis"'
        header_value = 'some-value; charset="us-ascii"'
        self.headers = {'Content-Type': content_type,
                        'X-Test-Header': header_value}

        resp = self.http_get('/')
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], content_type)
        self.assertEqual(hdrs['x-test-header'], header_value)

    def test_empty_to_one_addressable_relation(self):
        self.relation = tests.objects.ToOneAddressableRel(None)

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=None,
                links=dict(
                    self=dict(
                        href='/mycontext/42/relationships/myrelation',
                        meta=dict(faux=True),
                    ),
                ),
            )
        )

    def test_empty_to_one_relation_with_meta(self):
        self.relation = tests.objects.ToOneRel(None, meta=dict(a=1, b=2))

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(data, dict(data=None,
                                    meta=dict(a=1, b=2)))

    def test_empty_to_one_addressable_relation_with_meta(self):
        self.relation = tests.objects.ToOneAddressableRel(
            None, meta=dict(a=1, b=2))

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=None,
                links=dict(
                    self=dict(
                        href='/mycontext/42/relationships/myrelation',
                        meta=dict(faux=True),
                    ),
                ),
                meta=dict(
                    a=1,
                    b=2,
                ),
            )
        )

    def test_nonempty_to_one_relation(self):
        related = tests.objects.SimpleResource(attributes=dict(simple=True))
        self.relation = tests.objects.ToOneRel(related)

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=dict(id=related.id, type=related.type),
                links=dict(
                    related=related.links()['self'].href,
                ),
            )
        )

    def test_nonempty_to_one_addressable_relation(self):
        related = tests.objects.SimpleResource(attributes=dict(simple=True))
        self.relation = tests.objects.ToOneAddressableRel(related)

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=dict(id=related.id, type=related.type),
                links=dict(
                    related=related.links()['self'].href,
                    self=(f'/{related.type}/{related.id}'
                          f'/relationships/myrelation'),
                ),
            )
        )

    def test_nonempty_to_one_relation_with_meta(self):
        related = tests.objects.SimpleResource(attributes=dict(simple=True))
        self.relation = tests.objects.ToOneRel(related, meta=dict(a=1, b=2))

        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=dict(id=related.id, type=related.type),
                links=dict(
                    related=related.links()['self'].href,
                ),
                meta=dict(a=1, b=2),
            )
        )

    def test_nonempty_to_one_addressable_relation_with_meta(self):
        related = tests.objects.SimpleResource(attributes=dict(simple=True))
        self.relation = tests.objects.ToOneAddressableRel(
            related,
            meta=dict(a=1, b=2),
        )
        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(
            data,
            dict(
                data=dict(id=related.id, type=related.type),
                links=dict(
                    related=related.links()['self'].href,
                    self=(f'/{related.type}/{related.id}'
                          f'/relationships/myrelation'),
                ),
                meta=dict(
                    a=1,
                    b=2,
                ),
            )
        )

    def test_to_many_relation_non_empty(self):
        create_collection(self)
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        expected = dict(
            data=[
                dict(type=self.r1.type, id=self.r1.id),
                dict(type=self.r2.type, id=self.r2.id),
            ],
            links=dict(
                related='/api/baggage',
                self='/',
            ),
        )
        self.assertEqual(data, expected)

    def test_to_many_relation_filterable_with_filter(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?filter=something', status=None)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        expected = dict(
            data=[
                dict(type=self.r1.type, id=self.r1.id),
                dict(type=self.r2.type, id=self.r2.id),
            ],
            meta=dict(
                filter='something',
            ),
            links=dict(
                related='/api/baggage',
                self='/?filter=something',
            ),
        )
        self.assertEqual(data, expected)

    def test_to_many_relation_pagable_without_page(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IPagableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        expected = dict(
            data=[
                dict(type=self.r1.type, id=self.r1.id),
                dict(type=self.r2.type, id=self.r2.id),
            ],
            links=dict(
                related='/api/baggage',
                self='/',
            ),
        )
        self.assertEqual(data, expected)

    def test_to_many_relation_pagable_with_page(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IPagableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?page[start]=10&page[limit]=10')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        expected = dict(
            data=[
                dict(type=self.r1.type, id=self.r1.id),
                dict(type=self.r2.type, id=self.r2.id),
            ],
            meta=dict(
                page=dict(limit='10', start='10'),
            ),
            links=dict(
                related='/api/baggage',
                self='/?page[start]=10&page[limit]=10',
            ),
        )
        self.assertEqual(data, expected)

    def test_to_many_relation_sortable_with_sort(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.ISortableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?sort=somefield', status=None)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        expected = dict(
            data=[
                dict(type=self.r1.type, id=self.r1.id),
                dict(type=self.r2.type, id=self.r2.id),
            ],
            meta=dict(
                sort='somefield',
            ),
            links=dict(
                related='/api/baggage',
                self='/?sort=somefield',
            ),
        )
        self.assertEqual(data, expected)

    def test_to_many_relation_not_filterable_with_filter(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IPagableCollection,
            kt.jsonapi.interfaces.ISortableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?filter=something', status=None)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('filtering is not supported by collection', message)

    def test_to_many_relation_not_pagable_with_page(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
            kt.jsonapi.interfaces.ISortableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?page[start]=10&page[limit]=10', status=None)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('pagination is not supported by collection', message)

    def test_to_many_relation_not_sortable_with_sort(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
            kt.jsonapi.interfaces.IPagableCollection,
        )
        self.relation = tests.objects.ToManyRel(
            self.collection,
            related_link=kt.jsonapi.link.Link('/api/baggage'),
            self_link=kt.jsonapi.link.Link('/'),
        )
        resp = self.http_get('/?sort=somefield', status=None)
        self.assertEqual(resp.headers['Content-Type'], 'application/json')
        message = resp.json['message']
        self.assertIn('sorting is not supported by collection', message)

    def test_untyped_relation_fails(self):
        self.relation = tests.objects.UntypedRel()

        with self.assertRaises(TypeError) as cm:
            self.http_get('/')

        self.assertEqual(
            str(cm.exception),
            'relationship value does not provide a concrete relationship type')

    def test_adapts_collection_paging_links(self):
        source = tests.objects.SimpleResource()
        collection = tests.test_relation.FauxPagableCollection(
            links=dict(self=kt.jsonapi.link.Link('/some-things')))
        self.relation = kt.jsonapi.relation.ToManyRelationship(
            source, collection, addressable=True, name='things')
        source_link = source.links()['self'].href

        resp = self.http_get('/')
        links = resp.json['links']
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        link = links['first']
        self.assertIsInstance(link, str)
        self.assertEqual(link, links['self'])

        link = links['next']
        self.assertIsInstance(link, str)
        self.assertEqual(
            link,
            f'{source_link}/relationships/things?page[start]=15')

    def test_adapts_collection_paging_links_forwards_nonpaging(self):
        source = tests.objects.SimpleResource()
        collection = tests.test_relation.FauxPagableCollection(
            links=dict(self=kt.jsonapi.link.Link('/some-things')))
        self.relation = kt.jsonapi.relation.ToManyRelationship(
            source, collection, addressable=True, name='things')
        source_link = source.links()['self'].href

        resp = self.http_get('/?appOption=42')
        links = resp.json['links']
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        link = links['first']
        self.assertIsInstance(link, str)
        self.assertEqual(link, links['self'])
        self.assertIn('appOption=42', link)

        link = links['next']
        self.assertIsInstance(link, str)
        self.assertEqual(
            link,
            f'{source_link}/relationships/things?page[start]=15&appOption=42')


class ResourceResponseTestCase(tests.utils.JSONAPITestCase):

    def test_passing_headers_through(self):
        header_value = 'some-value; charset="us-ascii"'
        headers = {'X-Test-Header': header_value}

        resp = self.prepare_passing_headers_through(headers)
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], 'application/vnd.api+json')
        self.assertEqual(hdrs['x-test-header'], header_value)

    def test_provided_content_type_overrides(self):
        content_type = 'text/annoying; charset="shift-jis"'
        header_value = 'some-value; charset="us-ascii"'
        headers = {'Content-Type': content_type,
                   'X-Test-Header': header_value}

        resp = self.prepare_passing_headers_through(headers)
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], content_type)
        self.assertEqual(hdrs['x-test-header'], header_value)

    def prepare_passing_headers_through(self, headers):
        resource = tests.objects.SimpleResource(attributes=dict(simple=True))

        class Render(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().resource(resource,
                                                         headers=headers)

        self.api.add_resource(Render, '/')

        return self.http_get('/')

    def test_misc_values_no_include(self):
        data = self.check_misc_values_no_included_resources()
        self.assertNotIn('included', data)

    def test_misc_values_empty_include(self):
        # JSON:API 1.1 will require an `included` value, even if empty,
        # if the request specified `include` in the query string.
        # https://github.com/json-api/json-api/issues/1230
        data = self.check_misc_values_no_included_resources('?include=')
        self.assertEqual(data['included'], [])

    def test_misc_values_no_relevant_include(self):
        # JSON:API 1.1 will require an `included` value, even if empty,
        # if the request specified `include` in the query string.
        # https://github.com/json-api/json-api/issues/1230
        data = self.check_misc_values_no_included_resources(
            '?include=pecan,pie')
        self.assertEqual(data['included'], [])

    def check_misc_values_no_included_resources(self, query_string=''):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().resource(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_get('/' + query_string)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected = dict(
            id=resource.id,
            type=resource.type,
            attributes={
                'basic-attr': 42,
                'list-attr': ['a', 'b', 'c'],
                'string-attr': 'text',
            },
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
            relationships=dict(
                configuration=dict(
                    data=dict(type=related.type, id=related.id),
                    links=dict(related=related.links()['self'].href),
                    meta=dict(last_updated='tomorrow'),
                ),
            ),
        )
        self.assertEqual(data['data'], expected)
        return data

    def test_misc_values_included_resource(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().resource(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_get('/?include=pecan,configuration,pie')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected = dict(
            id=resource.id,
            type=resource.type,
            attributes={
                'basic-attr': 42,
                'list-attr': ['a', 'b', 'c'],
                'string-attr': 'text',
            },
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
            relationships=dict(
                configuration=dict(
                    data=dict(type=related.type, id=related.id),
                    links=dict(related=related.links()['self'].href),
                    meta=dict(last_updated='tomorrow'),
                ),
            ),
        )
        self.assertEqual(data['data'], expected)
        included = [dict(
            type=related.type,
            id=related.id,
            links=dict(
                self=related.links()['self'].href,
            ),
        )]
        self.assertEqual(data['included'], included)

    def test_resource_with_app_query_params(self):
        resource = tests.objects.SimpleResource(
            attributes={'basic': 42,
                        'string': 'text'},
            meta={'version': 24},
        )

        class Render(flask_restful.Resource):
            def get(self):
                return kt.jsonapi.api.context().resource(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_get('/?beta=frob&alfa=24')
        body = resp.json
        self.assertEqual(
            body['links'],
            dict(
                self=f'/baggage/{resource.id}?beta=frob&alfa=24',
            ),
        )

    def test_resource_suppress_all_fields(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().resource(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_get('/?fields[%s]=' % resource.type)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
        )
        self.assertEqual(data['data'], expected)
        self.assertNotIn('included', data)

    def test_resource_includes_suppressed_relation(self):
        related0 = tests.objects.SimpleResource(type='empty')
        relation0 = tests.objects.ToOneRel(related0)
        related1 = tests.objects.SimpleResource(type='empty')
        relation1 = tests.objects.ToOneRel(related1)
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation0,
                           'extension': relation1},
        )

        class Render(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().resource(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_get(
            f'/?fields[{resource.type}]=string-attr&include=configuration')
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected_resource = dict(
            id=resource.id,
            type=resource.type,
            attributes={'string-attr': 'text'},
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
        )
        included_resource = dict(
            id=related0.id,
            links=dict(
                self=f'/{related0.type}/{related0.id}',
            ),
            type=related0.type,
        )
        self.assertEqual(data['data'], expected_resource)
        self.assertEqual(data['included'], [included_resource])


class CreatedResponseTestCase(ResourceResponseTestCase):

    location = 'http://example.test/some-thing/42'

    def prepare_passing_headers_through(self, headers):
        resource = tests.objects.SimpleResource(attributes=dict(simple=True))

        class Render(flask_restful.Resource):
            def post(inst):
                return kt.jsonapi.api.context().created(resource,
                                                        headers=headers,
                                                        location=self.location)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/')
        self.assertEqual(resp.headers['Location'], self.location)
        return resp

    def check_misc_values_no_included_resources(self, query_string=''):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def post(inst):
                return kt.jsonapi.api.context().created(resource,
                                                        location=self.location)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/' + query_string)
        self.assertEqual(resp.headers['Location'], self.location)
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        data = resp.json
        expected = dict(
            id=resource.id,
            type=resource.type,
            attributes={
                'basic-attr': 42,
                'list-attr': ['a', 'b', 'c'],
                'string-attr': 'text',
            },
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
            relationships=dict(
                configuration=dict(
                    data=dict(type=related.type, id=related.id),
                    links=dict(related=related.links()['self'].href),
                    meta=dict(last_updated='tomorrow'),
                ),
            ),
        )
        self.assertEqual(data['data'], expected)
        return data

    def test_misc_values_included_resource(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def post(inst):
                return kt.jsonapi.api.context().created(resource,
                                                        location=self.location)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/?include=pecan,configuration,pie')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(resp.headers['Location'], self.location)
        data = resp.json
        expected = dict(
            id=resource.id,
            type=resource.type,
            attributes={
                'basic-attr': 42,
                'list-attr': ['a', 'b', 'c'],
                'string-attr': 'text',
            },
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
            relationships=dict(
                configuration=dict(
                    data=dict(type=related.type, id=related.id),
                    links=dict(related=related.links()['self'].href),
                    meta=dict(last_updated='tomorrow'),
                ),
            ),
        )
        self.assertEqual(data['data'], expected)
        included = [dict(
            type=related.type,
            id=related.id,
            links=dict(
                self=related.links()['self'].href,
            ),
        )]
        self.assertEqual(data['included'], included)

    def test_resource_suppress_all_fields(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            attributes={'basic-attr': 42,
                        'list-attr': ['a', 'b', 'c'],
                        'string-attr': 'text'},
            meta={'version': 24},
            relationships={'configuration': relation},
        )

        class Render(flask_restful.Resource):
            def post(inst):
                return kt.jsonapi.api.context().created(resource,
                                                        location=self.location)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/?fields[%s]=' % resource.type)
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertEqual(resp.headers['Location'], self.location)
        data = resp.json
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
        )
        self.assertEqual(data['data'], expected)
        self.assertNotIn('included', data)

    def test_created_self_link_meta(self):
        resource = tests.objects.SimpleResource(
            attributes={'basic': 42,
                        'string': 'text'},
        )
        orig_links = resource.links

        def faux_links():
            links = orig_links()
            return dict(
                self=kt.jsonapi.link.Link(
                    href=links['self'].href,
                    meta=dict(extra=42),
                )
            )

        class Render(flask_restful.Resource):
            def post(inst):
                resource.links = faux_links
                return kt.jsonapi.api.context().created(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/?appParam=seven')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        body = resp.json
        self.assertEqual(body['links']['self'],
                         f'/{resource.type}/{resource.id}?appParam=seven')

    def test_created_without_location(self):
        resource = tests.objects.SimpleResource(
            attributes={'basic': 42,
                        'string': 'text'},
        )

        class Render(flask_restful.Resource):
            def post(inst):
                return kt.jsonapi.api.context().created(resource)

        self.api.add_resource(Render, '/')

        resp = self.http_post('/')
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        self.assertNotIn('Location', resp.headers)


class CollectionResponseTestCase(tests.utils.JSONAPITestCase):

    def setUp(self):
        super(CollectionResponseTestCase, self).setUp()
        self.headers = None

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.collection(self.collection,
                                               headers=self.headers)

        self.api.add_resource(Render, '/')

    def test_passing_headers_through(self):
        header_value = 'some-value; charset="us-ascii"'
        headers = {'X-Test-Header': header_value}

        resp = self.prepare_passing_headers_through(headers)
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], 'application/vnd.api+json')
        self.assertEqual(hdrs['x-test-header'], header_value)

    def test_provided_content_type_overrides(self):
        content_type = 'text/annoying; charset="shift-jis"'
        header_value = 'some-value; charset="us-ascii"'
        headers = {'Content-Type': content_type,
                   'X-Test-Header': header_value}

        resp = self.prepare_passing_headers_through(headers)
        hdrs = resp.headers

        self.assertEqual(hdrs['content-type'], content_type)
        self.assertEqual(hdrs['x-test-header'], header_value)

    def prepare_passing_headers_through(self, headers):
        collection = tests.objects.SimpleCollection()

        class HeaderPassthrough(flask_restful.Resource):
            def get(inst):
                return kt.jsonapi.api.context().collection(collection,
                                                           headers=headers)

        self.api.add_resource(HeaderPassthrough, '/with-headers')

        return self.http_get('/with-headers')

    def test_empty(self):
        self.collection = tests.objects.SimpleCollection()

        resp = self.http_get('/', status=None)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        self.assertEqual(data, dict(data=[],
                                    links=dict(self='/')))

    def test_empty_with_query_params(self):
        self.collection = tests.objects.SimpleCollection()
        orig_links = self.collection.links

        def faux_links():
            links = orig_links()
            for k, v in links.items():
                v.meta = lambda: dict(faux=True, link_name=k)
            return links

        self.collection.links = faux_links

        resp = self.http_get('/?a=1&b=2&a=3', status=None)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')

        self.assertEqual(
            data,
            dict(
                data=[],
                links=dict(
                    self=dict(
                        href='/?a=1&b=2&a=3',
                        meta=dict(
                            faux=True,
                            link_name='self',
                        ),
                    ),
                ),
            ),
        )

    def test_empty_with_meta(self):
        self.collection = tests.objects.SimpleCollection(
            meta=dict(azumith=65.5, altitude=10356))

        resp = self.http_get('/', status=None)
        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        expected = dict(
            data=[],
            links=dict(
                self='/',
            ),
            meta=dict(
                altitude=10356,
                azumith=65.5,
            ),
        )
        self.assertEqual(data, expected)

    def test_with_content(self):
        create_collection(self)

        resp = self.http_get('/')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/'),
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_with_null_pagination_links(self):
        create_collection(self)
        self.collection._links.update(
            self=kt.jsonapi.link.Link('/'),
            first=None,
            next=None,
            prev=None,
            last=None,
        )

        resp = self.http_get('/')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        links = dict(
            self='/',
            first=None,
            next=None,
            prev=None,
            last=None,
        )
        self.assertEqual(data['links'], links)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_filterable_with_content_without_filter(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
        )

        resp = self.http_get('/')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/'),
            # No filter in meta, since not provided in query string.
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_filterable_with_content_with_filter(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
        )

        resp = self.http_get('/?filter=something')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/?filter=something'),
            meta=dict(filter='something'),
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 1)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_pagable_with_content_without_pagination(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IPagableCollection,
        )

        resp = self.http_get('/')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/'),
            # No page in meta, since not provided in query string.
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    maxDiff = None

    def test_pagable_with_content_with_pagination(self):
        self.r1 = tests.objects.SimpleResource(attributes=dict(simple=True))
        self.r2 = tests.objects.SimpleResource(attributes=dict(simple=False),
                                               meta=dict(last=True))
        self.collection = SimplePagableCollection([self.r1, self.r2])

        resp = self.http_get('/?page[limit]=15&page[start]=7&Extra=42')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(
                self='/?page[limit]=15&page[start]=7&Extra=42',
                next=None,
                prev=None,
            ),
            meta=dict(page=dict(limit='15', start='7')),
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 1)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_sortable_with_content_without_sort(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.ISortableCollection,
        )

        resp = self.http_get('/')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/'),
            # No sort in meta, since not provided in query string.
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_sortable_with_content_with_sort(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.ISortableCollection,
        )

        resp = self.http_get('/?sort=field0,-field1')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(self='/?sort=field0,-field1'),
            meta=dict(sort='field0,-field1')
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 1)

    def test_everything_with_content_with_everything(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
            kt.jsonapi.interfaces.IPagableCollection,
            kt.jsonapi.interfaces.ISortableCollection,
        )

        resp = self.http_get('/?sort=field0,-field1&filter=something'
                             '&page[limit]=15&page[start]=7')

        data = resp.json
        self.assertEqual(resp.headers['Content-Type'],
                         'application/vnd.api+json')
        with self.request_context('/'):
            empty_context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(empty_context, self.r1)
        d2 = kt.jsonapi.serializers.resource(empty_context, self.r2)
        expected = dict(
            data=[d1, d2],
            links=dict(
                self=('/?sort=field0,-field1&filter=something'
                      '&page[limit]=15&page[start]=7'),
            ),
            meta=dict(
                filter='something',
                page=dict(limit='15', start='7'),
                sort='field0,-field1',
            )
        )
        self.assertEqual(data, expected)
        self.assertEqual(self.collection.ncalls_resources, 1)
        self.assertEqual(self.collection.ncalls_set_filter, 1)
        self.assertEqual(self.collection.ncalls_set_pagination, 1)
        self.assertEqual(self.collection.ncalls_set_sort, 1)

    def test_included_does_not_duplicate(self):
        create_collection(self)
        r3 = tests.objects.SimpleResource(type='shared', attributes={'x': 42,
                                                                     'y': 24})
        self.r1._relationships = dict(
            thing=tests.objects.ToOneRel(r3, meta=dict(n=0)),
        )
        self.r2._relationships = dict(
            thing=tests.objects.ToOneRel(r3, meta=dict(n=1)),
        )

        resp = self.http_get('/?include=thing&fields[shared]=x,q')
        with self.request_context('/?fields[shared]=x'):
            context = kt.jsonapi.api.context()
        d1 = kt.jsonapi.serializers.resource(context, self.r1)
        d2 = kt.jsonapi.serializers.resource(context, self.r2)
        d3 = kt.jsonapi.serializers.resource(context, r3)
        expected = dict(
            data=[d1, d2],
            included=[d3],
            links=dict(self='/?include=thing&fields[shared]=x,q'),
        )
        self.assertEqual(resp.json, expected)

    def test_included_with_paged_collection(self):
        create_collection(self)
        zope.interface.alsoProvides(
            self.collection, kt.jsonapi.interfaces.IPagableCollection)

        r1 = tests.objects.SimpleResource(type='refd',
                                          attributes=dict(count=1))
        r2 = tests.objects.SimpleResource(type='refd',
                                          attributes=dict(count=2))
        c1 = tests.objects.SimpleCollection(
            [r1, r2],
            links=dict(self=kt.jsonapi.link.Link('/collections/a')),
        )
        zope.interface.alsoProvides(
            c1, kt.jsonapi.interfaces.IPagableCollection)
        self.r1._relationships['things'] = tests.objects.ToManyRel(
            c1, related_link=c1.links()['self'])

        r3 = tests.objects.SimpleResource(type='refd',
                                          attributes=dict(count=3))
        r4 = tests.objects.SimpleResource(type='refd',
                                          attributes=dict(count=4))
        c2 = tests.objects.SimpleCollection(
            [r3, r4],
            links=dict(self=kt.jsonapi.link.Link('/collections/b')),
        )
        zope.interface.alsoProvides(
            c2, kt.jsonapi.interfaces.IPagableCollection)
        self.r2._relationships['things'] = tests.objects.ToManyRel(
            c2, related_link=c2.links()['self'])

        resp = self.http_get('/?include=things&page[limit]=10')
        body = resp.json
        expected = dict(
            data=[
                dict(
                    attributes=dict(simple=True),
                    id=self.r1.id,
                    links=dict(self=f'/{self.r1.type}/{self.r1.id}'),
                    relationships=dict(
                        things=dict(
                            data=[
                                dict(type=r1.type, id=r1.id),
                                dict(type=r2.type, id=r2.id),
                            ],
                            links=dict(related='/collections/a'),
                        ),
                    ),
                    type=self.r1.type,
                ),
                dict(
                    attributes=dict(simple=False),
                    id=self.r2.id,
                    links=dict(self=f'/{self.r2.type}/{self.r2.id}'),
                    meta=dict(last=True),
                    relationships=dict(
                        things=dict(
                            data=[
                                dict(type=r3.type, id=r3.id),
                                dict(type=r4.type, id=r4.id),
                            ],
                            links=dict(related='/collections/b'),
                        ),
                    ),
                    type=self.r2.type,
                ),
            ],
            included=[
                dict(
                    attributes=dict(count=1),
                    id=r1.id,
                    links=dict(self=f'/{r1.type}/{r1.id}'),
                    type=r1.type,
                ),
                dict(
                    attributes=dict(count=2),
                    id=r2.id,
                    links=dict(self=f'/{r2.type}/{r2.id}'),
                    type=r2.type,
                ),
                dict(
                    attributes=dict(count=3),
                    id=r3.id,
                    links=dict(self=f'/{r3.type}/{r3.id}'),
                    type=r3.type,
                ),
                dict(
                    attributes=dict(count=4),
                    id=r4.id,
                    links=dict(self=f'/{r4.type}/{r4.id}'),
                    type=r4.type,
                ),
            ],
            links=dict(
                self='/?include=things&page[limit]=10',
            ),
            meta=dict(
                page=dict(
                    limit='10',
                )
            ),
        )
        self.maxDiff = None
        self.assertEqual(body, expected)


class CollectionPropertyQueryStringMismatchTestCase(
        tests.utils.JSONAPITestCase):

    def setUp(self):
        super(CollectionPropertyQueryStringMismatchTestCase, self).setUp()

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                with self.assertRaises(werkzeug.exceptions.BadRequest) as cm:
                    self.context.collection(self.collection)
                self.exception = cm.exception

        self.api.add_resource(Render, '/')

    def test_not_filterable_with_filter(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IPagableCollection,
            kt.jsonapi.interfaces.ISortableCollection,
        )

        self.http_get('/?sort=field0,-field1&filter=something'
                      '&page[limit]=15&page[start]=7')

        self.assertIsInstance(self.exception,
                              werkzeug.exceptions.BadRequest)
        self.assertEqual(self.exception.description,
                         'filtering is not supported by collection')
        self.assertEqual(self.collection.ncalls_resources, 0)
        self.assertEqual(self.collection.ncalls_set_filter, 0)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)

    def test_not_pagable_with_page(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
            kt.jsonapi.interfaces.ISortableCollection,
        )

        self.http_get('/?sort=field0,-field1&filter=something'
                      '&page[limit]=15&page[start]=7')

        self.assertIsInstance(self.exception,
                              werkzeug.exceptions.BadRequest)
        self.assertEqual(self.exception.description,
                         'pagination is not supported by collection')
        self.assertEqual(self.collection.ncalls_resources, 0)
        self.assertEqual(self.collection.ncalls_set_filter, 1)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 1)

    def test_not_sortable_with_sort(self):
        create_collection(
            self,
            kt.jsonapi.interfaces.IFilterableCollection,
            kt.jsonapi.interfaces.IPagableCollection,
        )

        self.http_get('/?sort=field0,-field1&filter=something'
                      '&page[limit]=15&page[start]=7')

        self.assertIsInstance(self.exception,
                              werkzeug.exceptions.BadRequest)
        self.assertEqual(self.exception.description,
                         'sorting is not supported by collection')
        self.assertEqual(self.collection.ncalls_resources, 0)
        self.assertEqual(self.collection.ncalls_set_filter, 1)
        self.assertEqual(self.collection.ncalls_set_pagination, 0)
        self.assertEqual(self.collection.ncalls_set_sort, 0)
