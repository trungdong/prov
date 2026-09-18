# Type-check code that uses prov

`prov` ships inline type annotations and a `py.typed` marker, so mypy and pyright check
your calls against them with no stub package. This guide covers the attribute arguments,
`attributes` and `other_attributes`, which are where a strict checker most often
objects. It describes `prov` 3.2.2 and later.

## Pass attributes as a dict

A dict literal written in the call type-checks, whatever mix of names and values it holds:

```python
import datetime

from prov.model import PROV, PROV_LABEL, PROV_TYPE, ProvDocument

document = ProvDocument()
document.add_namespace("ex", "http://example.org/")

report = document.entity(
    "ex:report",
    {
        PROV_LABEL: "Quarterly report",
        PROV_TYPE: PROV["Collection"],
        "ex:pages": 12,
        "ex:filed": datetime.datetime(2026, 9, 18),
    },
)
```

A dict built before the call type-checks too when its values share one type:

```python
labels = {PROV_LABEL: "Quarterly report"}
document.entity("ex:summary", labels)
```

## Annotate a dict that mixes value types

mypy infers a dict that is built before the call, with values of more than one type, as
`dict[str, object]`, and reports the call. Annotate the variable with
{py:data}`~prov.model.AttributeValue`, the type of the values an attribute accepts:

```python
from prov.model import AttributeValue

details: dict[str, AttributeValue] = {"ex:pages": 12, "ex:status": "filed"}
document.entity("ex:appendix", details)
```

Pyright accepts the call without the annotation.

`AttributeValue` covers `str`, `int`, `float`, `bool`, `datetime.datetime`,
{py:class}`~prov.identifier.Identifier`, {py:class}`~prov.model.QualifiedName`,
{py:class}`~prov.model.Literal`, any {py:class}`~prov.model.ProvRecord`, and `None`. A
record stands for its identifier. A `None` value is skipped.

## Pass attributes as pairs

A list, tuple, set or iterator of `(name, value)` pairs is accepted as well. Use pairs to
give one attribute several values, which a dict cannot hold:

```python
document.entity("ex:filing", [(PROV_TYPE, "ex:Report"), (PROV_TYPE, "ex:Filing")])
```

The values in pairs are typed `Any`, so a checker does not examine them.

A value whose static type is `Iterable[...]` or `Collection[...]` is reported, although it
works at runtime. Wrap it in `list()`, or type it as a `Sequence`, a `Set` or an
`Iterator`:

```python
from collections.abc import Iterable


def review_attributes() -> Iterable[tuple[str, str]]:
    yield ("ex:reviewer", "ex:alice")


document.entity("ex:review", list(review_attributes()))
```

## Give other values an XSD datatype

A checker reports a dict value of any other type, such as `decimal.Decimal`,
`datetime.date` or `bytes`. Those values have no PROV form, and `prov` cannot serialise
them faithfully. Write the value as a {py:class}`~prov.model.Literal` with its XSD
datatype:

```python
from prov.model import XSD, XSD_DECIMAL, Literal

document.entity(
    "ex:invoice",
    {
        "ex:total": Literal("1250.50", XSD_DECIMAL),
        "ex:due": Literal("2026-10-31", XSD["date"]),
    },
)
```
