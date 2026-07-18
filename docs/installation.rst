============
Installation
============

**Python 3 is required**.

At the command line::

    $ python -m pip install prov

This installs the core data model, PROV-JSON support, and the write-only PROV-N
serializer. Several features live behind optional extras and raise
``ModuleNotFoundError`` (naming the extra to install) if used without them:

- ``prov[rdf]`` — PROV-O/RDF serialization (``rdflib``).
- ``prov[xml]`` — PROV-XML serialization (``lxml``).
- ``prov[dot]`` — graphical export via Graphviz (``prov.dot``, ``prov_to_dot()``); also
  needs a local ``graphviz`` binary.
- ``prov[graph]`` — NetworkX graph interop (``prov.graph``, ``prov_to_graph()``/
  ``graph_to_prov()``).
- ``prov[plot]`` — the interactive-display path of ``ProvBundle.plot()``/
  ``ProvDocument.plot()`` (pulls in ``matplotlib`` as well as the ``dot`` extra's
  dependencies, since ``plot()`` renders through ``prov.dot``).

Extras combine, e.g.::

    $ python -m pip install "prov[rdf,xml,dot,graph]"

See ``docs/dependencies.md`` for the rationale behind each dependency and its version
pin.
