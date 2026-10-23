# prov.constants

`prov.constants` holds the PROV vocabulary as module-level data: the `prov`, `xsd` and
`xsi` namespaces; one {py:class}`~prov.identifier.QualifiedName` per record type
(`PROV_ENTITY`, `PROV_ACTIVITY`, ...), per formal attribute (`PROV_ATTR_ENTITY`,
`PROV_ATTR_TIME`, ...) and per extra attribute (`PROV_TYPE`, `PROV_LABEL`, ...); the XSD
datatypes (`XSD_STRING`, `XSD_INT`, ...); and the tables that map record types to their
PROV-N keywords and base types and formal attributes to their names. `prov.model` re-exports
every name, so `prov.model.PROV_TYPE` is the same object. Each is documented below in source
order.

```{eval-rst}
.. automodule:: prov.constants
   :members:
```
