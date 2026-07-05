# prov.constants

`prov.constants` defines the PROV-DM/PROV-O vocabulary as module-level data: one
{py:class}`~prov.identifier.QualifiedName` constant per record type and per formal attribute
(`PROV_ENTITY`, `PROV_ACTIVITY`, `PROV_ATTR_TIME`, ...), plus the lookup tables used to
translate between them and the Python classes — `PROV_N_MAP` (record type to PROV-N keyword),
`PROV_BASE_CLS` (record type to base class), and the various `PROV_ATTRIBUTE*`/`PROV_RECORD*`
sets and dicts consulted while parsing and serializing. `prov.model` imports this module with
`from prov.constants import *`, so these names are also available as `prov.model.PROV_*`; they
are documented here, once, to avoid duplicate entries.

```{eval-rst}
.. automodule:: prov.constants
   :members:
```
