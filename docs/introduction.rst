Introduction
============

The `JSON:API specification`_ deals with data models represented in REST
service interactions, and how they should be serialized.  While the
model presented is fairly clear, generating low-level structures in
JSON:API can be tedious.  Since there's a significant concept of
*resource type* in the specification, we can push type-specific aspects
into adapters that can be re-used systematically.

JSON:API provides standard ways to assemble compound documents that
include data for resources related to the 'primary data' being returned
with the response, as well as ways to request sparse field sets for
different resource types.  These are handled in a generic way using the
:mod:`kt.jsonapi` APIs, avoiding the need to implement these mechanisms
in each application, or for each endpoint that needs to support these
features.

The data model supported by the specification classifies non-error
responses into three categories: resources, collections, and
relationships.  Any given response will return one of these as the
response's *primary data*; additional resources may be included
depending on whether the client has requested related content to be
included (see `Inclusion of Related Resources`_).

Let's define a few terms:

application objects
    *Application objects* are the objects used to implement the core
    capabilities of your application.  They are responsible to providing
    operations that implement changes and maintain integrity of the
    data.  These objects usually correlate closely with representations
    of their data in the application's data storage system, but do not
    have to.  For example, a blog application might have objects
    representing authors and articles.

interfaces
    An *interface* is a definition of how an object presents it's
    capabilities.  It consists of method & attribute descriptions, and
    documentation.  Interfaces do *not* include any implementation.
    `Abstract Base Classes`_ provided with the Python standard library
    are similar, but are not the same because they can provide a mix of
    definition and implementation.

adapters
    An *adapter* is an object that wraps another object (or in some
    cases, multiple objects) to provide a different set of methods and
    attributes.  This is most commonly done to *adapt* an object to
    suitable for use with a particular framework or library.  A common
    use is to *adapt* application objects to interfaces required by
    presentation layers.

component architecture
    A *component architecture* is a system that supports defining
    interfaces, declaring that specific objects provide specific
    interfaces, registering adapters for specific conversions, and
    requesting adapters when needed.

Since JSON:API provides a strongly opinionated view on how resources,
relationships, and collections should be represented in a REST API, it
has a data model for these objects, and that may not correlate directly
to the models implemented in our application objects.  We can, however,
describe the JSON:API models using interfaces, as well as the models
provided by our application objects.  Additional classes can be defined
that map our application models to the JSON:API models; these will be
registered as adapters, allowing a library that knows how to work with
the JSON:API models to *adapt* application objects to objects that
present the JSON:API models.

The `Zope Component Architecture`_ (ZCA) is the most widely used
component architecture, since being developed for `Zope 3`_ application
platform.  It provides a number of capabilities beyond what we need for
our immediate needs, but is the dominant platform for interface-based
adaptation in Python.  This system allows declaring the interfaces
provided by objects using declarations at the class definitions; for a
class said to *implement* an interface, each instance will be determined
to *provide* that interface by default.  There is a lot of documentation
and literature on the ZCA online; we'll demonstrate essential aspects in
this document, but won't cover the ZCA beyond that.

.. seealso::

    These packages define the `Zope Component Architecture`_:

    |zope.component|_
        Adapter registration and retrieval support.  When calling an
        interface to perform adaptation, this is the machinery that's
        invoked.

    |zope.interface|_
        Support for interface definitions and support for declaring what
        classes or factories implement, and manipulation of what objects
        provide.

    |zope.schema|_
        More extensive support for typed data attributes.


Supporting JSON:API via adaptation
----------------------------------

Let's walk through a basic example of using interfaces and adaptation to
provide JSON:API serialization for some application objects.  The
JSON:API documents user simple ``author`` and ``article``  resources,
where each ``article`` has exactly one ``author``.

Let's start with simple definitions of the author and article mentioned
earlier.  This definition will track only a title, author, and an
identifier (that could be provided by the data storage system). ::

    import uuid

    class Author:

        def __init__(self, title):
            self.name = name
            self.identity = str(uuid.uuid4)

    class Article:

        def __init__(self, title, author):
            self.title = title
            self.author = author
            self.identity = str(uuid.uuid4)

Note that one of these attributes is a simple data value (``title``),
while the other is a reference to another application object
(``author``).

Generating a JSON:API representation of an ``Article`` requires being
able to adapt it to the :class:`~kt.jsonapi.interfaces.IResource`
interface.  (Interfaces defined by this library are in the
:mod:`kt.jsonapi.interfaces` module.)  For this, we'll need an
implementation of :class:`~kt.jsonapi.interfaces.IResource` that
takes an instance of :class:`Article` as an argument::

    import kt.jsonapi.interfaces
    import kt.jsonapi.link
    import zope.interface

    @zope.interface.implementer(kt.jsonapi.interfaces.IResource)
    class ArticleResource:

        def __init__(self, article):
            self.context = article
            self.type = 'article'

        def attributes(self):
            return dict(title=self.context.title)

        @property
        def id(self):
            return self.context.identity

        def links(self):
            return dict(
                self=kt.jsonapi.link.Link('/articles/' + self.id),
            )

        def meta(self):
            return dict()

        def relationships(self):
            return dict(author=Relationship(self.author))

    @zope.interface.implementer(kt.jsonapi.interfaces.IToOneRelationship)
    class Relationship:

        def __init__(self, related):
            self.related = kt.jsonapi.interfaces.IResource(related)

        def links(self):
            rlinks = self.related.links()
            if 'self' in rlinks:
                return dict(related=rlinks['self'])
            else:
                return dict()

        def meta(self):
            return dict()

        def resource(self):
            return self.related

Adapter implementations can inherit from other classes like anything
else, but we're keeping this simple for expository value.

Our adapters will need to be registered with the component architecture.
This requires that the object they adapt also be described by an
interface, so we'll need interfaces to describe our application
objects::


    class IAuthor(zope.interface.Interface):

        name = zope.schema.Text(
            title='name',
            description='Full name of an author.',
        )

    class IArticle(zope.interface.Interface):

        title = zope.schema.Text(
            title='Title',
            description='Title of the article.',
        )

        author = zope.schema.Object(
            title='Author',
            description='Author of the article.',
            interface=IAuthor,
        )

The application classes can be decorated to declare they implement these
interfaces::

    @zope.interface.implementer(IAuthor)
    class Author:
        # ...

    @zope.interface.implementer(IArticle)
    class Article:
        # ...

The adapters can now be registered with the component architecture::

    import zope.comonent

    zope.component.provideAdapter(ArticleResource, [IArticle])

Since adapters are often closely associated with the specific interfaces
they adapt, an adapter can be decorated with information on what is
adapted; this improves the locality of the definition, and can simplify
the registration in many cases.  In our example, it could look like this::

    @zope.component.adapter(IArticle)
    @zope.interface.implementer(kt.jsonapi.interfaces.IResource)
    class ArticleResource:
        # ...

    zope.component.provideAdapter(ArticleResource)

This form should be preferred when it applies, especially if adapter
registrations are more separated from their definitions (often the case
in larger frameworks).

Now that we have our application objects and adapters from those to the
JSON:API support interfaces, we can take a look at what it takes to
generate a JSON:API response for a request.  Let's create an endpoint to
return an article::

    import flask_restful
    import kt.jsonapi.api

    class ArticleEndpoint(flask_restful.Resource):

        def get(self, aid):
            article = get_article(aid)

            # Get the JSON:API context for the request.
            context = kt.jsonapi.api.context()

            return context.resource(article)

If this is registered with a URL path like ``'/articles/<string:aid>'``,
a GET request can be used to retrieve any article.  More interestingly,
a client can now request that the author be included as well by adding
the query parameter ``include=author``; the :mod:`kt.jsonapi`
implementation will handle building a compound document for the
response based on parameters defined in the specification.

The 'JSON:API context' object is responsible for interpreting the query
parameters defined by the JSON:API specification and provides a small
number of methods to generate responses;
:meth:`~kt.jsonapi.api.Context.resource` is the method to generate a
response with a single resource as the primary data.  Additional methods
are provided on the :class:`~kt.jsonapi.api.Context` object to generate
responses containing a relationship or collection as primary data.


.. _Abstract Base Classes:
   https://docs.python.org/3/library/abc.html

.. _Inclusion of Related Resources:
   https://jsonapi.org/format/#fetching-includes

.. _JSON\:API specification:
   https://jsonapi.org/format/

.. _Zope Component Architecture:
   https://zopecomponent.readthedocs.io/en/latest/narr.html

.. _Zope 3:
   https://en.wikipedia.org/wiki/Zope

.. |zope.component| replace:: ``zope.component``
.. _zope.component:
   https://zopecomponent.readthedocs.io/en/latest/

.. |zope.interface| replace:: ``zope.interface``
.. _zope.interface:
   https://zopeinterface.readthedocs.io/en/latest/

.. |zope.schema| replace:: ``zope.schema``
.. _zope.schema:
   https://zopeschema.readthedocs.io/en/latest/
