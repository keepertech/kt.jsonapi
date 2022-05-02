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

    def __init__(self, href, rel=None, describedby=None, title=None,
                 type=None, hreflang=None, meta=None):
        """Initialize link with href and optional metadata.

        :param href:
            URL reference of the link target.
        :param rel:
            The :rfc:`8288` relationship type of the link.
        :param describedby:
            Link to a description document describing the link target.
            This is usualy a specification such as OpenAPI, JSON Schema,
            or XML Schema.
        :param title:
            Human-facing title for the link, possibly suitable as a menu
            entry.  This is not necessarily the title of the linked
            document.
        :param type:
            Media type of the document referenced by *href*.
        :param hreflang:
            String or sequence of strings specifying languages the
            target document is available in.  Each entry must conform to
            :rfc:`5646`.
        :param meta:
            Mapping providing non-standard fields of additional data
            that should be serialized as the ``meta`` member of the link.

        """
        self.href = href
        self.rel = rel
        self.describedby = describedby
        self.title = title
        self.type = type
        self._hreflang = hreflang
        self._meta = meta or {}

    @property
    def hreflang(self):
        hreflang = self._hreflang
        if hreflang is None or isinstance(hreflang, str):
            return hreflang
        else:
            return list(hreflang)

    def meta(self):
        """Return metadata for this link.

        This returns a dictionary with the content passed to the
        constructor as *meta*, if any.  Otherwise, returns an empty
        dictionary.

        """
        return dict(self._meta)
