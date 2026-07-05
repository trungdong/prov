# Use the command-line tools

`prov` installs two console scripts: `prov-convert` (format/graphics conversion) and
`prov-compare` (equivalence checking). Both wrap the same {py:class}`~prov.model.ProvDocument`
API described in the other how-to pages.

## `prov-convert`

Convert a PROV-JSON document to PROV-N, PROV-XML, PROV-O/RDF, or any image format
supported by Graphviz.

### Synopsis

```bash
prov-convert [-h] [-f FORMAT] [-V] [infile] [outfile]
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format` | `FORMAT` | `json` | Output format: `json`, `xml`, `provn`, or any format name GraphViz's `dot` accepts (e.g. `svg`, `pdf`, `png`) |
| `-V`, `--version` | — | — | Print the version and exit |
| `-h`, `--help` | — | — | Print usage and exit |
| `infile` (positional) | — | stdin | Input file — **always read as PROV-JSON**, there is no input-format flag |
| `outfile` (positional) | — | stdout | Output file, written in `--format` |

`prov-convert` has no flag to choose the *input* format — the input is always
deserialized as PROV-JSON (`ProvDocument.deserialize(infile)`, which defaults to
`format="json"`). To convert from PROV-XML or RDF, load and re-serialize the document as
PROV-JSON first (or write a two-line Python script using
{py:meth}`~prov.model.ProvDocument.deserialize`/{py:meth}`~prov.model.ProvDocument.serialize`
directly — see the format-specific how-to pages).

### Examples

Convert a PROV-JSON file to PROV-N:

```bash
prov-convert -f provn document.json document.provn
```

Convert a PROV-JSON file to an SVG diagram (needs a local Graphviz install, see
{doc}`graphics`):

```bash
prov-convert -f svg document.json document.svg
```

Read from stdin, write PROV-JSON (the default) to stdout:

```bash
cat document.json | prov-convert > copy.json
```

### Exit behaviour

- Success: exit code `0`; the converted document is written to `outfile`.
- Unsupported `--format` value, or any other error (bad input, missing file): the error is
  printed to stderr prefixed with the program name, and the process exits with code `2`.

```bash
prov-convert -f bogus document.json out.bogus
# prov-convert: E: Output format "bogus" is not supported.
#               for help use --help
echo $?  # 2
```

## `prov-compare`

Compare two PROV documents for equivalence (after
{py:meth}`~prov.model.ProvBundle.unified`-style equality — the same `==` used throughout
`prov`), each independently loadable as PROV-JSON or PROV-XML.

### Synopsis

```bash
prov-compare [-h] [-f FORMAT1] [-F FORMAT2] [-V] [file1] [file2]
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format1` | `FORMAT1` | `json` | File 1's format: `json` or `xml` |
| `-F`, `--format2` | `FORMAT2` | `json` | File 2's format: `json` or `xml` |
| `-V`, `--version` | — | — | Print the version and exit |
| `-h`, `--help` | — | — | Print usage and exit |
| `file1`, `file2` (positional) | — | — | The two files to compare |

Although the help text says "`json` or `xml`", any format name registered with
{py:class}`prov.serializers.Registry` is actually accepted (e.g. `rdf`), because the flag
value is passed straight through to
{py:meth}`~prov.model.ProvDocument.deserialize`(format=...).

### Examples

Compare two PROV-JSON files:

```bash
prov-compare document.json copy.json
```

Compare a PROV-JSON file against a PROV-XML file:

```bash
prov-compare -f json -F xml document.json document.xml
```

### Exit behaviour

`prov-compare` has no textual "equal"/"different" output on success — it communicates the
result purely through the exit code:

- Exit code `0`: the two documents are equivalent (`doc1 == doc2`).
- Exit code `1`: the two documents differ (`doc1 != doc2`).
- Exit code `2`: an error occurred (e.g. a file could not be parsed); a message is printed
  to stderr.

```bash
prov-compare document.json document.json; echo $?   # 0 (identical)
prov-compare document.json copy2.json; echo $?       # 1 (different)
```
