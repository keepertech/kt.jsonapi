# (c) 2020.  Keeper Technology LLC.  All Rights Reserved.
# Use is subject to license.  Reproduction and distribution is strictly
# prohibited.
#
# Subject to the following third party software licenses and terms and
# conditions (including open source):  www.keepertech.com/thirdpartylicenses

"""\
Implementation of a simple link object.

"""

import zope.interface

import kt.jsonapi.interfaces


@zope.interface.implementer(kt.jsonapi.interfaces.ILink)
class Link(object):

    def __init__(self, href, **meta):
        self.href = href
        self._meta = meta

    def meta(self):
        return self._meta
