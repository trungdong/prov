# Prepare for prov 3.3.0

`prov` 3.3.0 rejects some input that 3.2.x reads, and reads a few other inputs
differently. From 3.2.3, `prov` warns about each such input with a
{py:class}`~prov.model.ProvFutureRejectionWarning` where it reads the input, and
still reads it as before. This guide shows how to find every such input in your
documents and code.

## Turn the warnings into errors

`ProvFutureRejectionWarning` is a subclass of {py:class}`~prov.model.ProvWarning`.
A filter on the subclass stops at the first affected input and leaves the other
`ProvWarning`s alone, such as the statements the `lenient` PROV-N profile skips.

From the command line:

```bash
python -W error::prov.model.ProvFutureRejectionWarning your_script.py
```

In a pytest configuration:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error::prov.model.ProvFutureRejectionWarning"]
```

In code:

```python
import warnings

from prov.model import ProvFutureRejectionWarning

warnings.simplefilter("error", ProvFutureRejectionWarning)
```

`prov` 3.3.0 keeps the class, so these filters keep working after the upgrade.

## Read the message

Each message ends with what 3.3.0 does instead, such as
"prov 3.3.0 will reject this". A message from a reader starts with the position
of the input: the line and column in PROV-N, or the record identifier and
attribute name in PROV-JSON.
