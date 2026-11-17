# Installation

`prov` needs Python 3.10.7 or later. On an earlier Python 3.10, pip installs 3.2.3 instead,
and on Python 3.9, 2.2.0.

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
| `pygments` | PROV-N syntax highlighting and `prov-convert --color` | `pygments` |

The `dot` and `plot` extras also need a local [Graphviz](https://graphviz.org/download/)
install, because rendering runs the `dot` executable.

Extras combine:

```bash
python -m pip install "prov[rdf,xml,dot,graph]"
```

[docs/dependencies.md](https://github.com/trungdong/prov/blob/main/docs/dependencies.md) in
the repository explains each dependency and its version pin.
