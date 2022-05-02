"""\
Tests for kt.jsonapi.serializers.

"""

import werkzeug.exceptions
import zope.component

import kt.jsonapi.api
import kt.jsonapi.error
import kt.jsonapi.interfaces
import kt.jsonapi.link
import kt.jsonapi.serializers
import tests.objects
import tests.utils


class ErrorSerializerTestCase(tests.utils.JSONAPITestCase):

    def test_empty_error(self):
        error = kt.jsonapi.error.Error()

        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidResultStructure) as cm:
            kt.jsonapi.serializers.error(error)

        message = str(cm.exception)
        self.assertIn(' for error', message)
        self.assertIn('serialization generated invalid structure', message)


class ToOneRelationshipSerializerTestCase(tests.utils.JSONAPITestCase):

    def test_empty_to_one_relationship_with_meta(self):
        relation = tests.objects.ToOneRel(
            None, meta={'last_updated': 'tomorrow'})
        data = kt.jsonapi.serializers.relationship(
            self.empty_context, relation)
        expected = dict(data=None,
                        meta=dict(last_updated='tomorrow'))
        self.assertEqual(data, expected)

    def test_basic_to_one_relationship_with_meta(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related,
                                          meta={'last_updated': 'tomorrow'})
        data = kt.jsonapi.serializers.relationship(
            self.empty_context, relation)
        expected = dict(
            data=dict(
                type=related.type,
                id=related.id,
            ),
            links=dict(
                related=related.links()['self'].href,
            ),
            meta=dict(
                last_updated='tomorrow',
            ),
        )
        self.assertEqual(data, expected)

    def test_basic_to_one_relationship_without_meta(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related)
        data = kt.jsonapi.serializers.relationship(
            self.empty_context, relation)
        expected = dict(
            data=dict(
                type=related.type,
                id=related.id,
            ),
            links=dict(
                related=related.links()['self'].href,
            ),
        )
        self.assertEqual(data, expected)

    def test_non_includable_to_one_relationship_included(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related)
        relation.includable = False

        with self.request_context('/?include=magic'):
            context = kt.jsonapi.api.context()

        with self.assertRaises(werkzeug.exceptions.BadRequest) as cm:
            kt.jsonapi.serializers.relationship(context, relation, 'magic')

        self.assertIn('cannot be included', cm.exception.description)

    def test_non_includable_to_one_relationship_not_included(self):
        related = tests.objects.SimpleResource(type='empty')
        relation = tests.objects.ToOneRel(related)
        relation.includable = False

        with self.request_context('/'):
            context = kt.jsonapi.api.context()

        rel = kt.jsonapi.serializers.relationship(context, relation)
        # In particular, there is no 'data' member in the relationship:
        expected = dict(
            links=dict(
                related=f'/empty/{related.id}',
            ),
        )
        self.assertEqual(rel, expected)

    def test_relationship_without_concrete_type(self):
        # Show that relationship objects need to be explicity to-one or
        # to-many; anything else is ill-defined.

        relation = tests.objects.UntypedRel()

        with self.assertRaises(TypeError) as cm:
            kt.jsonapi.serializers.relationship(self.empty_context, relation)

        message = str(cm.exception)
        self.assertEqual(
            message,
            'relationship value does not provide a concrete relationship type')


class ToManyRelationshipSerializerTestCase(tests.utils.JSONAPITestCase):

    def test_empty_with_meta(self):
        related_href = '/things/42/other-things'
        relation = tests.objects.ToManyRel(
            meta=dict(empty=True),
            related_link=kt.jsonapi.link.Link(related_href)
        )

        data = kt.jsonapi.serializers.relationship(
            self.empty_context, relation)

        expected = dict(
            data=[],
            links=dict(
                related=related_href,
            ),
            meta=dict(empty=True),
        )
        self.assertEqual(data, expected)

    def test_non_includable_to_many_relationship_included(self):
        r0 = tests.objects.SimpleResource(type='empty')
        r1 = tests.objects.SimpleResource(type='empty')
        coll = tests.objects.SimpleCollection([r0, r1])
        relation = tests.objects.ToManyRel(coll)
        relation.includable = False

        with self.request_context('/?include=magic'):
            context = kt.jsonapi.api.context()

        with self.assertRaises(werkzeug.exceptions.BadRequest) as cm:
            kt.jsonapi.serializers.relationship(context, relation, 'magic')

        self.assertIn('cannot be included', cm.exception.description)

    def test_non_includable_to_many_relationship_not_included(self):
        r0 = tests.objects.SimpleResource(type='empty')
        r1 = tests.objects.SimpleResource(type='empty')
        coll = tests.objects.SimpleCollection([r0, r1])
        relation = tests.objects.ToManyRel(
            coll, related_link=kt.jsonapi.link.Link('/some/things'))
        relation.includable = False

        with self.request_context('/'):
            context = kt.jsonapi.api.context()

        rel = kt.jsonapi.serializers.relationship(context, relation)
        # In particular, there is no 'data' member in the relationship:
        expected = dict(
            links=dict(
                related='/some/things',
            ),
        )
        self.assertEqual(rel, expected)


class ResourceSerializerTestCase(tests.utils.JSONAPITestCase):

    def test_empty(self):
        resource = tests.objects.SimpleResource(type='empty')
        data = kt.jsonapi.serializers.resource(self.empty_context, resource)
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(self=('/%s/%s' % (resource.type, resource.id))),
        )
        self.assertEqual(data, expected)

    def test_misc_values(self):
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
        data = kt.jsonapi.serializers.resource(self.empty_context, resource)
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
        self.assertEqual(data, expected)

    def test_empty_to_one_relationship(self):
        relation = tests.objects.ToOneRel(None)
        resource = tests.objects.SimpleResource(
            relationships={'configuration': relation},
        )
        data = kt.jsonapi.serializers.resource(self.empty_context, resource)
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(
                self=resource.links()['self'].href,
            ),
            relationships=dict(
                configuration=dict(data=None),
            ),
        )
        self.assertEqual(data, expected)

    def test_empty_to_one_relationship_with_meta(self):
        relation = tests.objects.ToOneRel(None,
                                          meta={'last_updated': 'tomorrow'})
        resource = tests.objects.SimpleResource(
            relationships={'configuration': relation},
        )
        data = kt.jsonapi.serializers.resource(self.empty_context, resource)
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(
                self=resource.links()['self'].href,
            ),
            relationships=dict(
                configuration=dict(
                    data=None,
                    meta=dict(last_updated='tomorrow'),
                ),
            ),
        )
        self.assertEqual(data, expected)

    def test_filtered_fields(self):
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
        with self.request_context('/?fields[baggage]=list-attr,string-attr'):
            context = kt.jsonapi.api.context()
        data = kt.jsonapi.serializers.resource(context, resource)
        expected = dict(
            id=resource.id,
            type=resource.type,
            attributes={
                'list-attr': ['a', 'b', 'c'],
                'string-attr': 'text',
            },
            links=dict(
                self=resource.links()['self'].href,
            ),
            meta=dict(version=24),
        )
        self.assertEqual(data, expected)

    def test_link_with_metadata(self):

        class ExtendedLinkResource(tests.objects.SimpleResource):

            def links(self):
                links = super(ExtendedLinkResource, self).links()
                links['self'] = kt.jsonapi.link.Link(
                    href=links['self'].href, meta=dict(cost=42))
                return links

        resource = ExtendedLinkResource(id='seven')
        data = kt.jsonapi.serializers.resource(self.empty_context, resource)
        href = '/%s/%s' % (resource.type, resource.id)
        expected = dict(
            id=resource.id,
            type=resource.type,
            links=dict(self=dict(href=href, meta=dict(cost=42))),
        )
        self.assertEqual(data, expected)

    def test_with_available_adapter(self):
        ob = tests.objects.AppObject(title='Top 10 Conundrums',
                                     author='Someone Like Me')
        self.addCleanup(zope.component.provideAdapter,
                        None, [tests.objects.IAppObject],
                        kt.jsonapi.interfaces.IResource)
        zope.component.provideAdapter(tests.objects.AppAdapter,
                                      [tests.objects.IAppObject])
        data = kt.jsonapi.serializers.resource(self.empty_context, ob)
        expected = dict(
            id='86',
            type='app-object',
            attributes=dict(
                title='Top 10 Conundrums',
                author='Someone Like Me',
            ),
            links=dict(self='/foo/86'),
        )
        self.assertEqual(data, expected)

    def test_without_available_adapter(self):
        ob = tests.objects.AppObject(title='Top 10 Conundrums',
                                     author='Someone Like Me')
        with self.assertRaises(TypeError) as cm:
            kt.jsonapi.serializers.resource(self.empty_context, ob)
        self.assertEqual(cm.exception.args[0], 'Could not adapt')

    def test_relationship_without_concrete_type(self):
        resource = tests.objects.SimpleResource(
            relationships={'thing': tests.objects.UntypedRel()},
        )

        with self.assertRaises(TypeError) as cm:
            kt.jsonapi.serializers.resource(self.empty_context, resource)

        message = str(cm.exception)
        self.assertEqual(
            message,
            'relationship value does not provide a concrete relationship type')

    def test_resource_without_self_link(self):
        # Sometimes, a resource may only be reachable via another
        # resource using ``include``, or as part of a collection.

        related = tests.objects.SimpleResource(
            attributes={'num': 42},
        )
        related.links = dict
        resource = tests.objects.SimpleResource(
            relationships={'thing': tests.objects.ToOneRel(related)},
        )

        with self.request_context('/?include=thing'):
            context = kt.jsonapi.api.context()
        data = kt.jsonapi.serializers.resource(context, resource)
        expected = dict(
            type=resource.type,
            id=resource.id,
            links=dict(
                self=resource.links()['self'].href,
            ),
            relationships=dict(
                thing=dict(
                    data=dict(
                        type=related.type,
                        id=related.id,
                    ),
                ),
            ),
        )
        self.assertEqual(data, expected)
        included = [dict(
            type=related.type,
            id=related.id,
            attributes=dict(num=42),
        )]
        self.assertEqual(context.included, included)


class LinkSerializerTestCase(tests.utils.JSONAPITestCase):

    def test_minimal_link(self):
        link = kt.jsonapi.link.Link(href='/big/bad/url/ref')

        data = kt.jsonapi.serializers.link(link)
        self.assertEqual(data, '/big/bad/url/ref')

    def test_maximal_link(self):
        link = kt.jsonapi.link.Link(
            href='/big/bad/url/ref',
            rel='copyright',
            describedby=kt.jsonapi.link.Link(
                '/big/bad/app/schema',
                type='application/x-myschema+xml'),
            title='Big Bad Document',
            type='application/json',
            hreflang=('en', 'fr', 'zh', 'x-leet'),
            meta=dict(structured='kinda-sorta'),
        )

        data = kt.jsonapi.serializers.link(link)
        expected = dict(
            href='/big/bad/url/ref',
            rel='copyright',
            describedby=dict(
                href='/big/bad/app/schema',
                type='application/x-myschema+xml',
            ),
            title='Big Bad Document',
            type='application/json',
            hreflang=['en', 'fr', 'zh', 'x-leet'],
            meta=dict(
                structured='kinda-sorta',
            ),
        )
        self.assertEqual(data, expected)
