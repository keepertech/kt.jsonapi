# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Tests for kt.jsonapi.relation.

"""

import kt.jsonapi.relation
import kt.jsonapi.interfaces
import tests.objects
import tests.utils


class ToOneRelationshipTestCase(tests.utils.JSONAPITestCase):

    def test_error_addressable_requires_name(self):
        source = tests.objects.SimpleResource()
        with self.assertRaises(ValueError) as cm:
            kt.jsonapi.relation.ToOneRelationship(source, None,
                                                  addressable=True)
        message = str(cm.exception)
        self.assertEqual(message, 'addressable relationships must have a name')

    def test_error_indirect_requires_name(self):
        source = tests.objects.SimpleResource()
        with self.assertRaises(ValueError) as cm:
            kt.jsonapi.relation.ToOneRelationship(source, None, indirect=True)
        message = str(cm.exception)
        self.assertEqual(message, 'indirect relationships must have a name')

    def test_error_addressable_indirect_requires_name(self):
        source = tests.objects.SimpleResource()
        with self.assertRaises(ValueError) as cm:
            kt.jsonapi.relation.ToOneRelationship(source, None,
                                                  addressable=True,
                                                  indirect=True)
        message = str(cm.exception)
        self.assertIn('must have a name', message)

    def test_empty_direct_unaddressable(self):
        source = tests.objects.SimpleResource()
        relation = kt.jsonapi.relation.ToOneRelationship(source, None)
        source._relationships['rel'] = relation

        self.assertTrue(
            kt.jsonapi.interfaces.IToOneRelationship(relation) is relation
        )
        self.assertIsNone(relation.resource())
        links = dict(relation.links())
        self.assertNotIn('related', links)
        self.assertNotIn('self', links)
        self.assertEqual(dict(relation.meta()), dict())

    def test_empty_indirect_unaddressable(self):
        source = tests.objects.SimpleResource()
        relation = kt.jsonapi.relation.ToOneRelationship(source, None, 'rel',
                                                         indirect=True)
        source._relationships['rel'] = relation

        self.assertTrue(
            kt.jsonapi.interfaces.IToOneRelationship(relation) is relation
        )
        self.assertIsNone(relation.resource())
        links = dict(relation.links())
        self.assertIn('related', links)
        source_href = source.links()['self'].href
        self.assertEqual(links['related'].href, source_href + '/rel')
        self.assertTrue(
            kt.jsonapi.interfaces.ILink.providedBy(links['related'])
        )
        self.assertNotIn('self', links)
        self.assertEqual(dict(relation.meta()), dict())

    def test_nonempty_direct_unaddressable(self):
        source = tests.objects.SimpleResource()
        target = tests.objects.SimpleResource()
        relation = kt.jsonapi.relation.ToOneRelationship(source, target, 'rel')
        source._relationships['rel'] = relation

        self.assertTrue(
            kt.jsonapi.interfaces.IToOneRelationship(relation) is relation
        )
        self.assertTrue(relation.resource(), target)
        links = dict(relation.links())
        target_href = target.links()['self'].href
        self.assertEqual(links['related'].href, target_href)
        self.assertTrue(
            kt.jsonapi.interfaces.ILink.providedBy(links['related'])
        )
        self.assertNotIn('self', links)
        self.assertEqual(dict(relation.meta()), dict())

    def test_nonempty_indirect_unaddressable(self):
        source = tests.objects.SimpleResource()
        target = tests.objects.SimpleResource()
        relation = kt.jsonapi.relation.ToOneRelationship(source, target, 'rel',
                                                         indirect=True)
        source._relationships['rel'] = relation

        self.assertTrue(
            kt.jsonapi.interfaces.IToOneRelationship(relation) is relation
        )
        self.assertTrue(relation.resource(), target)
        links = dict(relation.links())
        source_href = source.links()['self'].href
        self.assertEqual(links['related'].href, source_href + '/rel')
        self.assertTrue(
            kt.jsonapi.interfaces.ILink.providedBy(links['related'])
        )
        self.assertNotIn('self', links)
        self.assertEqual(dict(relation.meta()), dict())

    def test_addressable(self):
        source = tests.objects.SimpleResource()
        relation = kt.jsonapi.relation.ToOneRelationship(source, None, 'rel',
                                                         addressable=True)
        source._relationships['rel'] = relation

        links = dict(relation.links())
        source_href = source.links()['self'].href
        self.assertEqual(links['self'].href,
                         source_href + '/relationships/rel')


class ToManyRelationshipTestCase(tests.utils.JSONAPITestCase):

    def test_error_addressable_requires_name(self):
        source = tests.objects.SimpleResource()
        collection = tests.objects.SimpleCollection()
        with self.assertRaises(ValueError) as cm:
            kt.jsonapi.relation.ToManyRelationship(source, collection,
                                                   addressable=True)
        message = str(cm.exception)
        self.assertEqual(message, 'addressable relationships must have a name')

    def test_error_not_a_collection(self):
        source = tests.objects.SimpleResource()
        with self.assertRaises(TypeError) as cm:
            kt.jsonapi.relation.ToManyRelationship(source, object())
        message = str(cm.exception.args[0])
        self.assertEqual(message, 'Could not adapt')

    def test_addressable(self):
        source = tests.objects.SimpleResource()
        source_href = source.links()['self'].href
        collection = tests.objects.SimpleCollection(
            links=dict(self=kt.jsonapi.link.Link(source_href + '/chillun')))
        relation = kt.jsonapi.relation.ToManyRelationship(
            source, collection, 'rel', addressable=True)
        source._relationships['rel'] = relation

        links = dict(relation.links())
        self.assertEqual(links['related'].href,
                         source_href + '/chillun')
        self.assertEqual(links['self'].href,
                         source_href + '/relationships/rel')
        self.assertEqual(dict(relation.meta()), dict())
        self.assertIs(relation.collection(), collection)

    def test_unaddressable(self):
        source = tests.objects.SimpleResource()
        source_href = source.links()['self'].href
        collection = tests.objects.SimpleCollection(
            links=dict(self=kt.jsonapi.link.Link(source_href + '/chillun')))
        relation = kt.jsonapi.relation.ToManyRelationship(
            source, collection, 'rel')
        source._relationships['rel'] = relation

        links = dict(relation.links())
        self.assertEqual(links['related'].href,
                         source_href + '/chillun')
        self.assertNotIn('self', links)
        self.assertEqual(dict(relation.meta()), dict())
        self.assertIs(relation.collection(), collection)
