=====
Usage
=====

Simple PROV document
--------------------

.. code:: python

    import prov.model as prov
    import datetime

    document = prov.ProvDocument()

    document.set_default_namespace('http://anotherexample.org/')
    document.add_namespace('ex', 'http://example.org/')

    e2 = document.entity('e2', (
        (prov.PROV_TYPE, "File"),
        ('ex:path', "/shared/crime.txt"),
        ('ex:creator', "Alice"),
        ('ex:content', "There was a lot of crime in London last month"),
    ))

    a1 = document.activity('a1', datetime.datetime.now(), None, {prov.PROV_TYPE: "edit"})
    # References can be qnames or ProvRecord objects themselves
    document.wasGeneratedBy(e2, a1, None, {'ex:fct': "save"})
    document.wasAssociatedWith('a1', 'ag2', None, None, {prov.PROV_ROLE: "author"})
    document.agent('ag2', {prov.PROV_TYPE: 'prov:Person', 'ex:name': "Bob"})

    document.get_provn() # =>

    # document
    #   default <http://anotherexample.org/>
    #   prefix ex <http://example.org/>
    #   
    #   entity(e2, [prov:type="File", ex:creator="Alice",
    #               ex:content="There was a lot of crime in London last month",
    #               ex:path="/shared/crime.txt"])
    #   activity(a1, 2014-07-09T16:39:38.795839, -, [prov:type="edit"])
    #   wasGeneratedBy(e2, a1, -, [ex:fct="save"])
    #   wasAssociatedWith(a1, ag2, -, [prov:role="author"])
    #   agent(ag2, [prov:type="prov:Person", ex:name="Bob"])
    # endDocument

PROV document with a bundle
---------------------------

.. code:: python

    import prov.model as prov

    document = prov.ProvDocument()

    document.set_default_namespace('http://example.org/0/')
    document.add_namespace('ex1', 'http://example.org/1/')
    document.add_namespace('ex2', 'http://example.org/2/')

    document.entity('e001')

    bundle = document.bundle('e001')
    bundle.set_default_namespace('http://example.org/2/')
    bundle.entity('e001')

    document.get_provn() # =>

    # document
    #   default <http://example.org/0/>
    #   prefix ex2 <http://example.org/2/>
    #   prefix ex1 <http://example.org/1/>
    #   
    #   entity(e001)
    #   bundle e001
    #     default <http://example.org/2/>
    #     
    #     entity(e001)
    #   endBundle
    # endDocument

    document.serialize() # =>

    # {"prefix": {"default": "http://example.org/0/", "ex2": "http://example.org/2/", "ex1": "http://example.org/1/"}, "bundle": {"e001": {"prefix": {"default": "http://example.org/2/"}, "entity": {"e001": {}}}}, "entity": {"e001": {}}}

More examples
-------------

See `prov/tests/examples.py <https://github.com/trungdong/prov/blob/master/src/prov/tests/examples.py>`_
