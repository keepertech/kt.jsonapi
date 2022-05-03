"""\
Tests support for kt.jsonapi tests.

"""

import unittest

import flask
import flask_restful

import kt.jsonapi.api


class JSONAPITestCase(unittest.TestCase):

    def setUp(self):
        super(JSONAPITestCase, self).setUp()
        self.app = flask.Flask(__name__)
        self.app.config['PROPAGATE_EXCEPTIONS'] = True
        self.app.config['TESTING'] = True
        self.api = flask_restful.Api(self.app, catch_all_404s=True)
        self.client = self.app.test_client()
        with self.request_context('/'):
            self.empty_context = kt.jsonapi.api.context()

    def request_context(self, *args, **kwargs):
        return self.app.test_request_context(*args, **kwargs)

    def http_get(self, path, status=200):
        response = self.client.get(path)
        if status:
            self.assertEqual(
                response.status_code, status,
                f'GET {path} status {response.status_code}, expected {status}')
        return response

    def http_post(self, path, status=201, **kwargs):
        response = self.client.post(path, **kwargs)
        if status:
            self.assertEqual(
                response.status_code, status,
                f'POST {path} status {response.status_code}, expected {status}'
            )
        return response
