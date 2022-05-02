"""\
Tests for kt.jsonapi.error.

"""

import zope.schema

import kt.jsonapi.api
import kt.jsonapi.error
import kt.jsonapi.interfaces
import tests.utils


class ErrorsTestCase(tests.utils.JSONAPITestCase):

    def test_empty_errors(self):
        # Can't have an empty sequence of errors.
        with self.assertRaises(ValueError) as cm:
            kt.jsonapi.error.Errors([])

        self.assertEqual(str(cm.exception),
                         'sequence of errors cannot be empty')

    def test_errors_getitem(self):
        e0 = kt.jsonapi.error.Error(status=400)
        e1 = kt.jsonapi.error.Error(status=401)
        e2 = kt.jsonapi.error.Error(status=402)
        errors = kt.jsonapi.error.Errors([e0, e1, e2])

        self.assertIs(errors[2], e2)
        with self.assertRaises(IndexError):
            errors[3]

    def test_errors_len(self):
        e0 = kt.jsonapi.error.Error(status=400)
        e1 = kt.jsonapi.error.Error(status=401)
        e2 = kt.jsonapi.error.Error(status=402)
        errors = kt.jsonapi.error.Errors([e0, e1, e2])

        self.assertEqual(len(errors), 3)


class InvalidNameErrorAdaptationTestCase(tests.utils.JSONAPITestCase):

    def test_invalid_member_name(self):
        with self.request_context('/?fields[type]=ok,some junk'):
            with self.assertRaises(
                    kt.jsonapi.interfaces.InvalidMemberName) as cm:
                kt.jsonapi.api.context()
        exc = cm.exception
        self.assertTrue(
            kt.jsonapi.interfaces.IInvalidNameException.providedBy(exc))

        error = kt.jsonapi.error.invalidNameError(exc)

        errors = zope.schema.getValidationErrors(
            kt.jsonapi.interfaces.IError, error)
        self.assertEqual(list(errors), [])
        self.assertTrue(kt.jsonapi.interfaces.IError.providedBy(error))

        self.assertIn('Member name is invalid', error.title)
        self.assertEqual(error.status, 400)
        self.assertEqual(error.source(), dict(parameter='fields[type]'))
        self.assertEqual(error.meta(), dict(invalid_value='some junk'))

    def test_invalid_relationship_path(self):
        with self.request_context('/?include=onerelation,two relation'):
            with self.assertRaises(
                    kt.jsonapi.interfaces.InvalidRelationshipPath) as cm:
                kt.jsonapi.api.context()
        exc = cm.exception
        self.assertTrue(
            kt.jsonapi.interfaces.IInvalidNameException.providedBy(exc))

        error = kt.jsonapi.error.invalidNameError(exc)

        errors = zope.schema.getValidationErrors(
            kt.jsonapi.interfaces.IError, error)
        self.assertEqual(list(errors), [])
        self.assertTrue(kt.jsonapi.interfaces.IError.providedBy(error))

        self.assertIn('Relationship path includes invalid member name',
                      error.title)
        self.assertEqual(error.status, 400)
        self.assertEqual(error.source(), dict(parameter='include'))
        self.assertEqual(error.meta(), dict(invalid_value='two relation'))

    def test_invalid_type_name(self):
        with self.request_context('/?fields[abc def]=onefield,twofield'):
            with self.assertRaises(
                    kt.jsonapi.interfaces.InvalidTypeName) as cm:
                kt.jsonapi.api.context()
        exc = cm.exception
        self.assertTrue(
            kt.jsonapi.interfaces.IInvalidNameException.providedBy(exc))

        error = kt.jsonapi.error.invalidNameError(exc)

        errors = zope.schema.getValidationErrors(
            kt.jsonapi.interfaces.IError, error)
        self.assertEqual(list(errors), [])
        self.assertTrue(kt.jsonapi.interfaces.IError.providedBy(error))

        self.assertIn('Type name is invalid', error.title)
        self.assertEqual(error.status, 400)
        self.assertEqual(error.source(), dict(parameter='fields[abc def]'))
        self.assertEqual(error.meta(), dict(invalid_value='abc def'))


class InvalidStructureErrorAdaptationTestCase(tests.utils.JSONAPITestCase):

    def test_adapter(self):
        err = kt.jsonapi.error.Error()
        with self.request_context('/'):
            context = kt.jsonapi.api.context()
            with self.assertRaises(
                    kt.jsonapi.interfaces.InvalidResultStructure) as cm:
                context.error(err)
        exc = cm.exception
        self.assertTrue(
            kt.jsonapi.interfaces.IInvalidResultStructure.providedBy(exc))

        error = kt.jsonapi.error.invalidStructureError(exc)

        errors = zope.schema.getValidationErrors(
            kt.jsonapi.interfaces.IError, error)
        self.assertEqual(list(errors), [])
        self.assertTrue(kt.jsonapi.interfaces.IError.providedBy(error))

        self.assertEqual(error.status, 500)
        self.assertEqual(error.meta(), dict(structure_type='error'))


class QueryStringErrorAdaptationTestCase(tests.utils.JSONAPITestCase):

    def test_adapter(self):
        # Create a context from a bad query string, and capture the exception:
        with self.request_context('/?include[abc]=def'):
            with self.assertRaises(
                    kt.jsonapi.interfaces.QueryStringException) as cm:
                kt.jsonapi.api.context()
        exc = cm.exception
        self.assertTrue(
            kt.jsonapi.interfaces.IQueryStringException.providedBy(exc))

        error = kt.jsonapi.error.queryStringError(exc)

        errors = zope.schema.getValidationErrors(
            kt.jsonapi.interfaces.IError, error)
        self.assertEqual(list(errors), [])
        self.assertTrue(kt.jsonapi.interfaces.IError.providedBy(error))

        self.assertEqual(error.status, 400)
        self.assertIn('query string', error.title)
        self.assertIn('unsupported value', error.title)
        self.assertIn('value for query string key', error.detail)
        self.assertIn('key \'include\'', error.detail)
        self.assertIn('must not contain nested', error.detail)
        self.assertEqual(error.source(), {'parameter': 'include'})
