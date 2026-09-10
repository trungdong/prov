# prov.constants

`prov.constants` defines the PROV-DM and PROV-O vocabulary as module-level data. There is
one {py:class}`~prov.identifier.QualifiedName` constant per record type and per formal
attribute (`PROV_ENTITY`, `PROV_ACTIVITY`, `PROV_ATTR_TIME` and so on), plus the lookup
tables that translate between them and the Python classes. `PROV_N_MAP` maps a record type
to its PROV-N keyword and `PROV_BASE_CLS` to its base class. The `PROV_ATTRIBUTE*` and
`PROV_RECORD*` sets and dicts are consulted while parsing and serializing. `prov.model`
re-exports all of these, so they are also available as `prov.model.PROV_*`. They are
documented here once.

```{eval-rst}
.. automodule:: prov.constants
   :members:
```
