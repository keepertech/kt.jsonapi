# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Tests for kt.jsonapi.api.Context, .context().

"""

import flask

import kt.jsonapi.api
import tests.utils


class ContextClassTestCase(tests.utils.JSONAPITestCase):

    def get_context(self):
        return kt.jsonapi.api.Context(
            flask.current_app._get_current_object(),
            flask.request._get_current_object())

    def test_no_query_string(self):
        with self.request_context('/'):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(rc.fields, {})
        self.assertEqual(rc.relpaths, set())

    def test_fields_empty(self):
        with self.request_context('/?fields[abc]='):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(sorted(rc.fields), ['abc'])
        self.assertEqual(rc.fields['abc'], set())
        self.assertEqual(rc.relpaths, set())

    def test_fields_simple(self):
        with self.request_context('/?fields[abc]=a,b&fields[def]=e'):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(sorted(rc.fields), ['abc', 'def'])
        self.assertEqual(rc.fields['abc'], {'a', 'b'})
        self.assertEqual(rc.fields['def'], {'e'})
        self.assertEqual(rc.relpaths, set())

    def test_include_simple(self):
        with self.request_context('/?include=abc,def.ghi'):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(rc.fields, {})
        self.assertEqual(rc.relpaths, {'abc', 'def', 'def.ghi'})

    def test_include_invalid_simple(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidRelationshipPath) as cm:
            with self.request_context('/?include=def ghi'):
                self.get_context()
        self.assertEqual(cm.exception.value, 'def ghi')

    def test_include_invalid_relpath_1(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidRelationshipPath) as cm:
            with self.request_context('/?include=abc.def ghi'):
                self.get_context()
        self.assertEqual(cm.exception.field, 'def ghi')
        self.assertEqual(cm.exception.value, 'abc.def ghi')

    def test_include_invalid_relpath_2(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidRelationshipPath) as cm:
            with self.request_context('/?include=alternate,abc.def-ghi,'):
                self.get_context()
        self.assertEqual(cm.exception.field, '')
        self.assertEqual(cm.exception.value, '')

    def test_fields_include_together(self):
        with self.request_context(
                '/?fields[abc]=a,b&include=abc,def.ghi&fields[def]=e'):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(sorted(rc.fields), ['abc', 'def'])
        self.assertEqual(rc.fields['abc'], {'a', 'b'})
        self.assertEqual(rc.fields['def'], {'e'})
        self.assertEqual(rc.relpaths, {'abc', 'def', 'def.ghi'})

    def test_error_repeated_key_fields_sometype(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyUsage) as cm:
            with self.request_context(
                    '/?fields[sometype]=spam&fields[sometype]=spandex'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn('may have only one value', message)
        self.assertIn("query string key 'fields[sometype]'", message)
        self.assertEqual(cm.exception.key, 'fields[sometype]')

    def test_error_repeated_key_include(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyUsage) as cm:
            with self.request_context('/?include=spam&include=spandex'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn('may have only one value', message)
        self.assertIn("query string key 'include'", message)
        self.assertEqual(cm.exception.key, 'include')

    def test_error_container_already_value(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyUsage) as cm:
            with self.request_context('/?filter=spam&filter[kong]=spandex'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("'filter' is already a value field", message)
        self.assertIn("cannot be used as a container for 'filter[kong]'",
                      message)
        self.assertEqual(cm.exception.key, 'filter[kong]')

    def test_error_value_already_container(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyUsage) as cm:
            with self.request_context('/?filter[kong]=spam&filter=spandex'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("'filter' is already a container", message)
        self.assertIn("cannot be used as a value field", message)
        self.assertEqual(cm.exception.key, 'filter')

    def test_error_fields_not_container(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyValue) as cm:
            with self.request_context('/?fields=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("query string key 'fields' must", message)
        self.assertIn("map type names to lists of field names", message)
        self.assertEqual(cm.exception.key, 'fields')

    def test_error_fields_contains_no_containers(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyValue) as cm:
            with self.request_context('/?fields[type][name]=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("value for query string key 'fields[type]'", message)
        self.assertIn("must not contain nested containers", message)
        self.assertEqual(cm.exception.key, 'fields[type]')

    def test_error_fields_invalid_field_name(self):
        with self.assertRaises(kt.jsonapi.interfaces.InvalidMemberName) as cm:
            with self.request_context('/?fields[type]=ok,some junk'):
                self.get_context()
        self.assertEqual(cm.exception.value, 'some junk')
        # message = str(cm.exception)
        # self.assertEqual(message, '')
        # breakpoint()
        # self.assertIn("value for query string key 'fields[type]'", message)
        # self.assertIn("must not contain nested containers", message)
        # self.assertEqual(cm.exception.key, 'fields[type]')

    def test_error_include_cannot_be_container(self):
        with self.assertRaises(
                kt.jsonapi.interfaces.InvalidQueryKeyValue) as cm:
            with self.request_context('/?include[name]=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("value for query string key 'include'", message)
        self.assertIn("must not contain nested containers", message)
        self.assertEqual(cm.exception.key, 'include')

    def test_error_invalid_query_key_empty_segments_middle(self):
        with self.assertRaises(kt.jsonapi.interfaces.InvalidQueryKey) as cm:
            with self.request_context('/?include[][stuff]=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("empty names not allowed in query string keys", message)
        self.assertIn("'include[][stuff]'", message)
        self.assertEqual(cm.exception.key, 'include[][stuff]')

    def test_error_invalid_query_key_empty_segments_end(self):
        with self.assertRaises(kt.jsonapi.interfaces.InvalidQueryKey) as cm:
            with self.request_context('/?include[stuff][]=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn("empty names not allowed in query string keys", message)
        self.assertIn("'include[stuff][]'", message)
        self.assertEqual(cm.exception.key, 'include[stuff][]')

    def test_error_invalid_query_key_segments(self):
        with self.assertRaises(kt.jsonapi.interfaces.InvalidQueryKey) as cm:
            with self.request_context('/?include[stuff]foo=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn(
            "malformed query string key segment following 'include[stuff]'",
            message)
        self.assertIn(": 'foo'", message)
        self.assertEqual(cm.exception.key, 'include[stuff]foo')

    def test_error_invalid_query_key_property_segment(self):
        with self.assertRaises(kt.jsonapi.interfaces.InvalidQueryKey) as cm:
            with self.request_context('/?include[stuff=somejunk'):
                self.get_context()
        message = str(cm.exception)
        self.assertIn(
            "malformed query string key segment following 'include'", message)
        self.assertIn(": '[stuff'", message)
        self.assertEqual(cm.exception.key, 'include[stuff')

    # Demonstrate that we just ignore query parameters that do not start
    # with defined jsonapi query parameter names; were these
    # jsonapi-defined parameters, we'd be raising exceptions.

    def test_nonerror_repeated_key(self):
        self._check_non_jsonapi_params_non_error(
            '/?donkey=spam&donkey=spandex')

    def test_nonerror_container_already_value(self):
        self._check_non_jsonapi_params_non_error(
            '/?donkey=spam&donkey[kong]=spandex')

    def test_nonerror_value_already_container(self):
        self._check_non_jsonapi_params_non_error(
            '/?donkey[kong]=spam&donkey=spandex')

    def test_nonerror_malformed_key(self):
        # breakpoint()
        self._check_non_jsonapi_params_non_error('/?donkey[kong=spam')

    def test_nonerror_empty_segment_middle(self):
        self._check_non_jsonapi_params_non_error('/?donkey[][kong]=spam')

    def test_nonerror_empty_segment_end(self):
        self._check_non_jsonapi_params_non_error('/?donkey[kong][]=spam')

    def _check_non_jsonapi_params_non_error(self, urlpath):
        with self.request_context(urlpath):
            rc = self.get_context()
        self.assertIsInstance(rc.fields, dict)
        self.assertIsInstance(rc.relpaths, set)
        self.assertEqual(rc.fields, {})
        self.assertEqual(rc.relpaths, set())


class ContextGetterTestCase(ContextClassTestCase):

    def get_context(self):
        return kt.jsonapi.api.context()

    def test_getter_returns_same_context_for_same_request(self):
        with self.request_context('/?fields[abc]=a,b&fields[def]=e'):
            rc1 = kt.jsonapi.api.context()
            rc2 = kt.jsonapi.api.context()
        self.assertIs(rc1, rc2)

    def test_getter_returns_different_contexts_for_different_requests(self):
        with self.request_context('/?fields[abc]=a,b&fields[def]=e'):
            rc1 = kt.jsonapi.api.context()
        with self.request_context('/?fields[abc]=d,e'):
            rc2 = kt.jsonapi.api.context()
        self.assertIsNot(rc1, rc2)
        self.assertEqual(rc1.fields['abc'], {'a', 'b'})
        self.assertEqual(rc2.fields['abc'], {'d', 'e'})
