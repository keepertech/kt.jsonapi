# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

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
