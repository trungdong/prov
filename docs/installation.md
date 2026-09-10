# Installation

`prov` needs Python 3.10 or later.

```bash
python -m pip install prov
```

This installs the core data model and the PROV-JSON, PROV-JSONLD and PROV-N serializers.
PROV-N is write-only. Every other capability sits behind an optional extra and raises
`ModuleNotFoundError`, naming the extra to install, when used without it.

| Extra | Enables | Installs |
|---|---|---|
| `rdf` | PROV-O (RDF) serializer and deserializer | `rdflib` |
| `xml` | PROV-XML serializer and deserializer | `lxml` |
| `dot` | Graphviz export through `prov.dot` | `pydot`, `networkx` |
| `graph` | NetworkX conversion through `prov.graph` | `networkx` |
| `plot` | The interactive display in `ProvBundle.plot()` | `matplotlib`, `pydot`, `networkx` |

The `dot` and `plot` extras also need a local [Graphviz](https://graphviz.org/download/)
install, because rendering runs the `dot` executable.

Extras combine:

```bash
python -m pip install "prov[rdf,xml,dot,graph]"
```

[docs/dependencies.md](https://github.com/trungdong/prov/blob/main/docs/dependencies.md) in
the repository explains each dependency and its version pin.
