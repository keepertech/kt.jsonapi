"""\
Tests for various internal functions that represent isolated functionality.

"""

import unittest

import kt.jsonapi.api


class TestSplitKey(unittest.TestCase):

    def test_simple(self):
        obnames, field = kt.jsonapi.api._split_key('simple')
        self.assertEqual(obnames, ())
        self.assertEqual(field, 'simple')

    def test_segmented(self):
        obnames, field = kt.jsonapi.api._split_key('simple[sub][field]')
        self.assertEqual(obnames, ('simple', 'sub'))
        self.assertEqual(field, 'field')
