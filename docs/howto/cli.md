# Use the command-line tools

`prov` installs two console scripts. `prov-convert` converts a document between formats or
renders it as an image. `prov-compare` checks two documents for equivalence. Both wrap the
{py:class}`~prov.model.ProvDocument` API described in the other how-to guides.

## `prov-convert`

Convert a PROV-JSON document to PROV-N, PROV-XML, PROV-O (RDF), PROV-JSONLD, or any image
format Graphviz supports.

### Synopsis

```bash
prov-convert [-h] [-f FORMAT] [-V] [infile] [outfile]
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format` | `FORMAT` | `json` | Output format: `json`, `xml`, `rdf`, `jsonld`, `provn`, or any Graphviz output format such as `svg`, `pdf` or `png` |
| `-V`, `--version` | | | Print the version and exit |
| `-h`, `--help` | | | Print usage and exit |
| `infile` | | stdin | Input file, always read as PROV-JSON |
| `outfile` | | stdout | Output file, written in `--format` |

There is no flag for the input format. The input is always read as PROV-JSON. To convert
from another format, load the document in Python and serialize it with
{py:meth}`~prov.model.ProvDocument.serialize`, as the format guides show.

Image formats need the `dot` extra and a local Graphviz install. See {doc}`graphics`.

### Examples

Convert a PROV-JSON file to PROV-N:

```bash
prov-convert -f provn document.json document.provn
```

Convert a PROV-JSON file to an SVG diagram:

```bash
prov-convert -f svg document.json document.svg
```

Read from stdin and write PROV-JSON, the default, to stdout:

```bash
cat document.json | prov-convert > copy.json
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. The converted document is in `outfile`. |
| `2` | Error, such as an unsupported format, unreadable input or a missing file. The message goes to stderr. |

```bash
prov-convert -f bogus document.json out.bogus
# prov-convert: E: Output format "bogus" is not supported.
#               for help use --help
echo $?  # 2
```

## `prov-compare`

Compare two documents for equality, using the same `==` as the library. Each file may be
in any registered format.

### Synopsis

```bash
prov-compare [-h] [-f FORMAT1] [-F FORMAT2] [-V] [file1] [file2]
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format1` | `FORMAT1` | `json` | Format of `file1`: `json`, `xml`, `rdf` or `jsonld` |
| `-F`, `--format2` | `FORMAT2` | `json` | Format of `file2`: `json`, `xml`, `rdf` or `jsonld` |
| `-V`, `--version` | | | Print the version and exit |
| `-h`, `--help` | | | Print usage and exit |
| `file1`, `file2` | | | The two files to compare |

### Examples

Compare two PROV-JSON files:

```bash
prov-compare document.json copy.json
```

Compare a PROV-JSON file against a PROV-XML file:

```bash
prov-compare -f json -F xml document.json document.xml
```

### Exit codes

`prov-compare` prints nothing on success. The result is the exit code.

| Code | Meaning |
| --- | --- |
| `0` | The documents are equal. |
| `1` | The documents differ. |
| `2` | Error, such as a file that could not be parsed. The message goes to stderr. |

```bash
prov-compare document.json document.json; echo $?   # 0
prov-compare document.json copy2.json; echo $?       # 1
```
