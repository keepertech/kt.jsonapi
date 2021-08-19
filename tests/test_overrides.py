# (c) 2021.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Tests for context factory overrides.

"""

import flask_restful

import kt.jsonapi.api
import kt.jsonapi.error
import kt.jsonapi.link
import tests.utils


class OverrideMixin:

    def jsonapi(self):
        return self._jsonapi_data


class MagicContext(OverrideMixin, kt.jsonapi.api.Context):
    pass


class MagicErrorContext(OverrideMixin, kt.jsonapi.api.ErrorContext):
    pass


class OverridesTestCase(tests.utils.JSONAPITestCase):

    _jsonapi_data = dict(
        version='1.0',
    )
    _jsonapi_expected = dict(_jsonapi_data)

    def setUp(self):
        super(OverridesTestCase, self).setUp()
        OverrideMixin._jsonapi_data = self._jsonapi_data
        self.app.config['KT_JSONAPI_CONTEXT_REGULAR'] = MagicContext
        self.app.config['KT_JSONAPI_CONTEXT_ERROR'] = MagicErrorContext

    def test_collection_context_override(self):
        thing = tests.objects.SimpleCollection()

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.collection(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/')

        self.assertIsInstance(self.context, MagicContext)
        payload = resp.json
        self.assertNotIn('errors', payload)
        self.assertIn('data', payload)
        self.assertIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)

    def test_created_context_override(self):
        thing = tests.objects.SimpleResource(
            attributes=dict(simple=True),
        )

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.created(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/', status=201)

        self.assertIsInstance(self.context, MagicContext)
        payload = resp.json
        self.assertNotIn('errors', payload)
        self.assertIn('data', payload)
        self.assertIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)

    def test_error_context_override(self):
        thing = kt.jsonapi.error.Error(
            status=418,
            title='Not a teapot',
            detail='Use an appropriate appliance for the task at hand.',
            about=kt.jsonapi.link.Link(
                href='https://api.example.com/not-teapot'),
            code='not-teapot',
        )

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.error_context()
                return self.context.error(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/', status=418)

        self.assertIsInstance(self.context, MagicErrorContext)
        payload = resp.json
        self.assertIn('errors', payload)
        self.assertNotIn('data', payload)
        self.assertNotIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)

    def test_related_context_override(self):
        source = tests.objects.SimpleResource(
            attributes=dict(simple=True),
        )
        thing = tests.objects.ToOneAddressableRel(
            None,
            name='some-relation',
            source=source,
        )

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.related(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/')

        self.assertIsInstance(self.context, MagicContext)
        payload = resp.json
        self.assertNotIn('errors', payload)
        self.assertIn('data', payload)
        self.assertIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)

    def test_relationship_context_override(self):
        source = tests.objects.SimpleResource(
            attributes=dict(simple=True),
        )
        thing = tests.objects.ToOneAddressableRel(
            None,
            name='some-relation',
            source=source,
        )

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.relationship(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/')

        self.assertIsInstance(self.context, MagicContext)
        payload = resp.json
        self.assertNotIn('errors', payload)
        self.assertIn('data', payload)
        self.assertIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)

    def test_resource_context_override(self):
        thing = tests.objects.SimpleResource(
            attributes=dict(simple=True),
        )

        class Render(flask_restful.Resource):
            def get(inst):
                self.context = kt.jsonapi.api.context()
                return self.context.resource(thing)

        self.api.add_resource(Render, '/')
        resp = self.http_get('/')

        self.assertIsInstance(self.context, MagicContext)
        payload = resp.json
        self.assertNotIn('errors', payload)
        self.assertIn('data', payload)
        self.assertIn('links', payload)
        self.assertEqual(payload['jsonapi'], self._jsonapi_expected)


class MinimizingJSONAPIMetaTestCase(OverridesTestCase):

    _jsonapi_data = dict(
        version='1.0',
        meta=dict(),
    )


class ExpansizeJSONAPIObjectTestCase(OverridesTestCase):

    _jsonapi_data = dict(
        version='1.1',
        meta=dict(
            implementation='kt.jsonapi',
            version='1.4.2',
        ),
        exts=['https://jsonapi.org/ext/atomic'],
        profiles=['https://example.com/profile/foo',
                  'https://example.com/profile/bar'],
    )
    _jsonapi_expected = _jsonapi_data
