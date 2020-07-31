# (c) 2020 - 2021.  Keeper Technology LLC.  All Rights Reserved.
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
class Link:
    """Utility object representing a JSON:API link.

    This supports additional metadata fields allowed by JSON:API in
    addition to the required href value.

    """

    def __init__(self, href, meta=None):
        """Initialize link with href and optional metadata.

        :param href:
            URL reference of the link target.
        :param meta:
            Mapping providing non-standard fields of additional data
            that should be serialized as the ``meta`` member of the link.

        """
        self.href = href
        self._meta = meta or {}

    def meta(self):
        """Return metadata for this link.

        This returns a dictionary with the content passed to the
        constructor as *meta*, if any.  Otherwise, returns an empty
        dictionary.

        """
        return dict(self._meta)
