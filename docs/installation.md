# Installation

`prov` needs Python 3.11 or later. On Python 3.10, pip installs the last 3.2.x release
instead.

```bash
python -m pip install prov
```

This installs the core data model and the PROV-JSON, PROV-JSONLD and PROV-N serializers.
All three read and write out of the box, with no extra needed. Every other capability sits
behind an optional extra. Using one without its extra raises an error that names the extra
to install.

| Extra | Enables | Installs |
|---|---|---|
| `rdf` | PROV-O (RDF) serializer and deserializer | `rdflib` |
| `xml` | PROV-XML serializer and deserializer | `lxml` |
| `dot` | Graphviz export through `prov.dot` | `pydot`, `networkx` |
| `graph` | NetworkX conversion through `prov.graph` | `networkx` |
| `plot` | The interactive display in `ProvDocument.plot()` | `matplotlib`, `pydot`, `networkx` |
| `pygments` | Installs Pygments for PROV-N syntax highlighting; `prov` alone enables highlighting wherever Pygments is already present | `pygments` |

The `dot` and `plot` extras also need a local [Graphviz](https://graphviz.org/download/)
install, because rendering runs the `dot` executable.

Extras combine:

```bash
python -m pip install "prov[rdf,xml,dot,graph]"
```

[docs/dependencies.md](https://github.com/trungdong/prov/blob/main/docs/dependencies.md) in
the repository explains each dependency and its version pin.
