# prov-convert

## Synopsis

```bash
prov-convert [-h] [-i INPUT_FORMAT] [-f FORMAT] [-w NAME=VALUE] [-r NAME=VALUE]
             [--color {auto,always,never}] [-V] [infile] [outfile]
```

## Description

`prov-convert` converts a document between PROV-JSON, PROV-N, PROV-XML, PROV-O (RDF) and
PROV-JSONLD, or renders it as any image format Graphviz supports. It reads `infile` and
writes `outfile`, and standard input and standard output stand in for a missing or `-`
argument. It reads and parses the input before it opens `outfile`, so an input that fails
to read leaves an existing output file as it was. An error while writing can leave the
output file empty or partial ([#745](https://github.com/trungdong/prov/issues/745)), so
write to a new file and replace the old one after the command succeeds.

Both formats default to `auto`, which follows the extension table under Options.

Content detection cannot find RDF/XML. To read RDF/XML from standard input, pass
`-i rdf -r rdf_format=xml`.

## Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-i`, `--input-format` | `INPUT_FORMAT` | `auto` | Input format: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-f`, `--format` | `FORMAT` | `auto` | Output format: `auto`, `json`, `xml`, `rdf`, `jsonld`, `provn`, or any Graphviz output format such as `svg`, `pdf` or `png` |
| `-w`, `--writer-option` | `NAME=VALUE` | | Pass an option to the writer. Repeatable; the last of a repeated name wins |
| `-r`, `--reader-option` | `NAME=VALUE` | | Pass an option to the reader. Repeatable; the last of a repeated name wins |
| `--color` | `auto`, `always` or `never` | `auto` | Colour the output with Pygments. `auto` colours standard output on a terminal; `always` colours a file or pipe too; `never` writes plain text |
| `-V`, `--version` | | | Print the program name and version, such as `prov-convert 3.3.0`, and exit |
| `-h`, `--help` | | | Print usage and exit |
| `infile` | | stdin | Input file, read in `--input-format` |
| `outfile` | | stdout | Output file, written in `--format` |

Image formats need the `dot` extra and a local Graphviz install. See {doc}`../howto/graphics`.

Colour needs the `pygments` extra. `--color always` without Pygments is an error. The formats
with a lexer are `provn`, `json`, `jsonld`, `xml`, `dot` and `rdf` written as `turtle`,
`xml` or `json-ld`; every other format, including the default TriG, is written plain.
Under `auto`, `prov-convert` colours the output when no output file is named, standard
output is a terminal, Pygments imports and the format has a lexer. The two variables under
Environment also turn `auto` off.

Each `-w` or `-r` value is typed by one rule. `none` (any case) is `None`, `true` and
`false` (any case) are booleans, an optionally signed run of digits is an integer, and
anything else is a string. The value is everything after the first `=`. Each format accepts
only the names below, and any other name is an error that lists the accepted ones.

| Format | `-w` writer options | `-r` reader options |
| --- | --- | --- |
| `provn` | `strict`, `width` | `profile` |
| `json` | `indent`, `sort_keys`, `ensure_ascii` | none |
| `jsonld` | `context`, `indent`, `sort_keys`, `ensure_ascii` | none |
| `rdf` | `rdf_format` | `rdf_format` |
| `xml` | `force_types` | none |
| Graphviz formats | `show_nary`, `use_labels`, `direction`, `show_element_attributes`, `show_relation_attributes` | |

Only `profile` (PROV-N) and `rdf_format` (RDF) are reachable with `-r`. The JSON readers
take Python callables and the RDF reader's two mappers take dictionaries, which a command-line
string cannot supply, so the command line does not accept those names.

Under `auto`, the extension of the path (lower-cased) selects the format and, for RDF, the
`rdf_format` the reader or writer needs. For input, a path with any other extension, or
standard input, goes to content detection through {py:func}`prov.read`. An explicit `-i` or
`-f` always wins over the extension, and an `rdf_format` given with `-r` or `-w` overrides
the one the extension implies.

| Extension | Format | `rdf_format` |
| --- | --- | --- |
| `.json` | `json` | |
| `.provn` | `provn` | |
| `.xml`, `.provx` | `xml` | |
| `.jsonld` | `jsonld` | |
| `.ttl` | `rdf` | `turtle` |
| `.trig` | `rdf` | `trig` |
| `.nt` | `rdf` | `nt` |
| `.nq` | `rdf` | `nquads` |
| `.rdf` | `rdf` | `xml` |

For output, `auto` also selects a Graphviz output format when the extension names one, such
as `.svg`, `.png`, `.pdf` or `.dot`. Standard output, or any other extension such as
`.webp`, writes PROV-JSON, and `-f webp` exits 2.

A `.json` file is always read as PROV-JSON. To read a PROV-JSONLD file named `.json`, pass
`-i jsonld`.

## Environment

| Variable | Effect |
| --- | --- |
| `NO_COLOR` | When set and non-empty, turns `--color auto` off. |
| `TERM` | When `dumb`, turns `--color auto` off. |

## Exit status

| Code | Meaning |
| --- | --- |
| `0` | Success. The converted document is in `outfile`. |
| `2` | Error, such as an unsupported format or unreadable input. A runtime error prints one line, `prov-convert: error: <message>`, to stderr; a usage error or a file that cannot be opened prints argparse's usage line first. |
| `130` | Interrupted with Ctrl-C. Nothing is printed. |

## Examples

Convert a PROV-JSON file to PROV-N. The extension of `document.provn` selects the format,
so `-f provn` is optional here:

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

Write PROV-N with every statement on one line:

```bash
prov-convert -f provn -w width=none document.json document.provn
```

Read PROV-N leniently, and draw an SVG diagram with labels:

```bash
prov-convert -i provn -r profile=lenient document.provn document.json
prov-convert -f svg -w use_labels=true document.json document.svg
```

Read from standard input and write PROV-JSON to standard output:

```bash
cat document.json | prov-convert > copy.json
```

Page coloured PROV-N:

```bash
prov-convert --color always -f provn document.json | less -R
```

## See also

{doc}`prov-compare <prov-compare>`, the how-to {doc}`../howto/cli`, and
{py:func}`prov.read`. The full documentation is at <https://prov.readthedocs.io/>.
