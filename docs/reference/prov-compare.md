# prov-compare

Compare two PROV documents for equality.

## Synopsis

```bash
prov-compare [-h] [-f FORMAT1] [-r NAME=VALUE] [-F FORMAT2] [-R NAME=VALUE] [-V]
             file1 file2
```

## Description

`prov-compare` compares two documents with the same `==` as the library. Each file may be
in any registered format, and the two files need not share one. It prints nothing on
success, and the result is the exit status.

Each format defaults to `auto`, which takes the format from the file extension and
otherwise from the content, as `prov-convert` does.

## Options

| Flag | Argument | Default | Meaning |
| --- | --- | --- | --- |
| `-f`, `--format1` | `FORMAT1` | `auto` | Format of `file1`: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-F`, `--format2` | `FORMAT2` | `auto` | Format of `file2`: `auto`, `json`, `xml`, `rdf`, `jsonld` or `provn` |
| `-r`, `--reader-option1` | `NAME=VALUE` | | Pass an option to the reader of `file1`. Repeatable |
| `-R`, `--reader-option2` | `NAME=VALUE` | | Pass an option to the reader of `file2`. Repeatable |
| `-V`, `--version` | | | Print the program name and version, such as `prov-compare 3.3.0`, and exit |
| `-h`, `--help` | | | Print usage and exit |
| `file1`, `file2` | | | The two files to compare; `-` reads one of them from standard input |

Reader options are typed and checked as for `prov-convert -r`, and the extension table and
the options each format accepts are on the {doc}`prov-convert` page.

## Exit status

| Code | Meaning |
| --- | --- |
| `0` | The documents are equal. |
| `1` | The documents differ. |
| `2` | Error, such as a file that could not be parsed or opened. A runtime error prints one line, `prov-compare: error: <message>`, to stderr. A usage error or a missing file prints argparse's usage line first. |
| `130` | Interrupted with Ctrl-C. Nothing is printed. |

## Examples

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

## See also

{doc}`prov-convert(1) <prov-convert>` and the how-to {doc}`../howto/cli`.
