# API reference

This section documents every public class and function in `prov`, module by module, with
their type hints as shipped in the source (`prov` ships inline types via `py.typed`). It is
organised by concept rather than alphabetically — start with {doc}`model` for the core object
model, then follow the links below for identifiers, the PROV vocabulary, serializers, and the
graph/graphics interop modules, plus the {doc}`conformance` matrix mapping every PROV-DM concept
to its `prov` class, factory method, and serializer round-trip status. For task-oriented
walkthroughs, see the {doc}`../tutorial/getting-started`
and the {doc}`../howto/provjson` (and its sibling how-to pages) instead.

```{toctree}
:maxdepth: 1

model
identifier
constants
serializers
graph
dot
conformance
```
