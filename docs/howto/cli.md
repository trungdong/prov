# Use the command-line tools

`prov` installs two console scripts. `prov-convert` converts a document between formats or
renders it as an image. `prov-compare` checks two documents for equivalence. Both wrap the
{py:class}`~prov.model.ProvDocument` API described in the other how-to guides. From Python,
`prov.scripts.convert.main(argv)` and `prov.scripts.compare.main(argv)` run a tool on a list
of arguments and return its exit code.

## `prov-convert`

Convert a PROV document between PROV-JSON, PROV-N, PROV-XML, PROV-O (RDF) and PROV-JSONLD,
or render it as any image format Graphviz supports.

{doc}`../reference/prov-convert` lists every option, the formats each accepts, the environment
variables and the exit codes.

### Examples

Convert a PROV-JSON file to PROV-N:

```bash
prov-convert -f provn document.json document.provn
```

Convert a PROV-N file to PROV-JSON:

```bash
prov-convert -i provn -f json document.provn document.json
```

Image formats need the `dot` extra and a local Graphviz install. See {doc}`graphics`.

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

Colour needs the `pygments` extra. Page coloured PROV-N, or write Turtle with colour to a
terminal:

```bash
prov-convert --color always -f provn document.json | less -R
prov-convert -f rdf -w rdf_format=turtle document.json
```

Read from standard input and write PROV-JSON to standard output:

```bash
cat document.json | prov-convert > copy.json
```

An unsupported output format exits with status 2 and prints one line to standard error:

```bash
prov-convert -f bogus document.json out.bogus
# prov-convert: error: No serializer available for the format "bogus"
echo $?  # 2
```

## `prov-compare`

Compare two documents for equality, using the same `==` as the library. Each file may be
in any registered format.

{doc}`../reference/prov-compare` lists every option and the exit codes.

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

Equal documents exit with status 0, and different documents exit with status 1:

```bash
prov-compare document.json document.json; echo $?   # 0
prov-compare document.json copy2.json; echo $?       # 1
```
