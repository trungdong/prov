# Use the command-line tools

`prov` installs two console scripts. `prov-convert` converts a document between formats or
renders it as an image. `prov-compare` checks two documents for equivalence. Both wrap the
{py:class}`~prov.model.ProvDocument` API described in the other how-to guides. From Python,
`prov.scripts.convert.main(argv)` and `prov.scripts.compare.main(argv)` run a tool on a list
of arguments and return its exit code.

## `prov-convert`

Convert a PROV document between PROV-JSON, PROV-N, PROV-XML, PROV-O (RDF) and PROV-JSONLD,
or render it as any image format Graphviz supports.

### Synopsis

```bash
prov-convert [-h] [-i INPUT_FORMAT] [-f FORMAT] [-w NAME=VALUE] [-r NAME=VALUE]
             [--color {auto,always,never}] [-V] [infile] [outfile]
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-i`, `--input-format` | `INPUT_FORMAT` | `auto` | Input format: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-f`, `--format` | `FORMAT` | `auto` | Output format: `auto`, `json`, `xml`, `rdf`, `jsonld`, `provn`, or any Graphviz output format such as `svg`, `pdf` or `png` |
| `-w`, `--writer-option` | `NAME=VALUE` | | Pass an option to the writer. Repeatable; the last of a repeated name wins. |
| `-r`, `--reader-option` | `NAME=VALUE` | | Pass an option to the reader. Repeatable; the last of a repeated name wins. |
| `--color` | `auto`, `always` or `never` | `auto` | Colour the output with Pygments. `auto` colours standard output on a terminal; `always` colours a file or pipe too; `never` writes plain text |
| `-V`, `--version` | | | Print the program name and version, such as `prov-convert 3.3.0`, and exit |
| `-h`, `--help` | | | Print usage and exit |
| `infile` | | stdin | Input file, read in `--input-format` |
| `outfile` | | stdout | Output file, written in `--format` |

Image formats need the `dot` extra and a local Graphviz install. See {doc}`graphics`.

Colour needs the `pygments` extra. Under `auto`, `prov-convert` colours the output when no
output file is named, standard output is a terminal, `NO_COLOR` is unset or empty, `TERM` is
not `dumb` and Pygments imports. `--color always` without Pygments is an error. The formats
with a lexer are `provn`, `json`, `jsonld`, `xml`, `dot` and `rdf` written as `turtle`,
`xml` or `json-ld`; every other format, including the default TriG, is written plain.

A value is typed by one rule. `none` (any case) is `None`, `true` and `false` (any case) are
booleans, an optionally signed run of digits is an integer, and anything else is a string.
The value is everything after the first `=`. Each format accepts only the names below, and
any other name is an error that lists the accepted ones.

| Format | `-w` writer options | `-r` reader options |
| --- | --- | --- |
| `provn` | `strict`, `width` | `profile` |
| `json` | `indent`, `sort_keys`, `ensure_ascii` | `object_hook`, `object_pairs_hook`, `parse_constant`, `parse_float`, `parse_int` |
| `jsonld` | `context`, `indent`, `sort_keys`, `ensure_ascii` | the same as `json` |
| `rdf` | `rdf_format` | `rdf_format`, `predicate_mapper`, `relation_mapper` |
| `xml` | `force_types` | none |
| Graphviz formats | `show_nary`, `use_labels`, `direction`, `show_element_attributes`, `show_relation_attributes` | |

The JSON readers' names take Python callables, which the command line cannot supply.

### Examples

Convert a PROV-JSON file to PROV-N:

```bash
prov-convert -f provn document.json document.provn
```

Convert a PROV-N file to PROV-JSON:

```bash
prov-convert -i provn -f json document.provn document.json
```

Convert a PROV-JSON file to an SVG diagram:

```bash
prov-convert -f svg document.json document.svg
```

Write PROV-N with every statement on one line, as 3.2.3 did:

```bash
prov-convert -f provn -w width=none document.json document.provn
```

Write the strict PROV-N profile, or indent PROV-JSON:

```bash
prov-convert -f provn -w strict=true document.json document.provn
prov-convert -f json -w indent=2 document.json pretty.json
```

Read PROV-N leniently, and draw an SVG diagram with labels:

```bash
prov-convert -i provn -r profile=lenient document.provn document.json
prov-convert -f svg -w use_labels=true document.json document.svg
```

Page coloured PROV-N, or write Turtle with colour to a terminal:

```bash
prov-convert --color always -f provn document.json | less -R
prov-convert -f rdf -w rdf_format=turtle document.json
```

Read from stdin and write PROV-JSON to stdout. The default, `auto`, takes a file's format
from its extension and otherwise from its content, and an output to stdout or an unknown
extension is PROV-JSON:

```bash
cat document.json | prov-convert > copy.json
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. The converted document is in `outfile`. |
| `2` | Error, such as an unsupported format, unreadable input or a missing file. One line, `prov-convert: error: <message>`, goes to stderr. |
| `130` | Interrupted with Ctrl-C. Nothing is printed. |

```bash
prov-convert -f bogus document.json out.bogus
# prov-convert: error: No serializer available for the format "bogus"
echo $?  # 2
```

## `prov-compare`

Compare two documents for equality, using the same `==` as the library. Each file may be
in any registered format.

### Synopsis

```bash
prov-compare [-h] [-f FORMAT1] [-r NAME=VALUE] [-F FORMAT2] [-R NAME=VALUE] [-V]
             file1 file2
```

### Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format1` | `FORMAT1` | `auto` | Format of `file1`: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-F`, `--format2` | `FORMAT2` | `auto` | Format of `file2`: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-r`, `--reader-option1` | `NAME=VALUE` | | Pass an option to the reader of `file1`. Repeatable, typed as for `prov-convert -r`. |
| `-R`, `--reader-option2` | `NAME=VALUE` | | Pass an option to the reader of `file2`. Repeatable, typed as for `prov-convert -r`. |
| `-V`, `--version` | | | Print the program name and version, such as `prov-compare 3.3.0`, and exit |
| `-h`, `--help` | | | Print usage and exit |
| `file1`, `file2` | | | The two files to compare; `-` reads one of them from standard input |

### Examples

Compare two PROV-JSON files:

```bash
prov-compare document.json copy.json
```

Compare a PROV-JSON file against a PROV-XML file:

```bash
prov-compare -f json -F xml document.json document.xml
```

Compare a lenient PROV-N file against a Turtle file:

```bash
prov-compare -r profile=lenient -R rdf_format=turtle document.provn document.ttl
```

### Exit codes

`prov-compare` prints nothing on success. The result is the exit code.

| Code | Meaning |
| --- | --- |
| `0` | The documents are equal. |
| `1` | The documents differ. |
| `2` | Error, such as a file that could not be parsed. One line, `prov-compare: error: <message>`, goes to stderr. |
| `130` | Interrupted with Ctrl-C. Nothing is printed. |

```bash
prov-compare document.json document.json; echo $?   # 0
prov-compare document.json copy2.json; echo $?       # 1
```
