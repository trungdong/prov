# Use the command-line tools

`prov` installs two console scripts. `prov-convert` converts a document between formats or
renders it as an image. `prov-compare` checks two documents for equality. Both wrap the
{py:class}`~prov.model.ProvDocument` API described in the other how-to guides.

{doc}`../reference/prov-convert` and {doc}`../reference/prov-compare` list every option, the
formats each accepts, the environment variables, the exit codes and a set of basic examples.
This page shows tasks that those pages do not.

## Pass options to the writer

`-w NAME=VALUE` passes an option to the writer of the output format. Write PROV-N that
parses under the `strict` profile, or indent PROV-JSON:

```bash
prov-convert -f provn -w strict=true document.json document.provn
prov-convert -f json -w indent=2 document.json pretty.json
```

{doc}`provn` describes what `strict` changes.

## Write RDF to the terminal

With no output file, `prov-convert` writes to standard output. RDF defaults to TriG, so
ask for Turtle with `rdf_format`:

```bash
prov-convert -f rdf -w rdf_format=turtle document.json
```

## Read an error

A runtime error prints one line to standard error and exits with status 2:

```bash
prov-convert -f bogus document.json out.bogus
# prov-convert: error: No serializer available for the format "bogus"
echo $?  # 2
```
