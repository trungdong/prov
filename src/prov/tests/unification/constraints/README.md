# PROV-CONSTRAINTS unification corpus

153 PROV-XML documents exercising the W3C PROV-CONSTRAINTS unification and
key-constraint rules, consumed by `src/prov/tests/test_unification_constraints.py`
(characterization of `unified()`, roadmap step 30b; the 3.0 reimplementation is
roadmap step 36b — umbrella issue
[#253](https://github.com/trungdong/prov/issues/253)).

## Origin

Copied verbatim (retrieved 2026-07-11) from a local checkout of
[ProvToolbox](https://github.com/lucmoreau/ProvToolbox), the Java reference
implementation, at:

```
modules-validation/prov-validation/src/test/resources/validate/unification/*.xml
```

The source directory also carries a paired `.provn` file per case (consumed by
ProvToolbox's `ValidateTest.java`); only the `.xml` files are vendored here
because `prov` has no PROV-N parser. These cases derive from the test cases
assembled by the W3C Provenance Working Group for the PROV-CONSTRAINTS
implementation report (PROV-CONSTRAINTS is a W3C Recommendation, 2013-04-30,
<https://www.w3.org/TR/prov-constraints/>), as implemented and maintained in
ProvToolbox's validation module.

## Licence

ProvToolbox is distributed under an MIT-style licence (`license.txt` in its
repository root):

> Copyright (c) 2018–2023 King's College London,
> 2011–2017 University of Southampton
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to
> deal in the Software without restriction, including without limitation the
> rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
> sell copies of the Software [...] subject to [inclusion of] the above
> copyright notice and this permission notice [...]. THE SOFTWARE IS PROVIDED
> "AS IS", WITHOUT WARRANTY OF ANY KIND.

## Naming convention

Files are named `<category>-successN.xml` / `<category>-failN.xml`:

- `*-successN`: a **valid** instance — applying the PROV-CONSTRAINTS
  uniqueness/key constraints (§6.1, Constraints 22–29) normalizes it
  successfully (same-identifier statements merge; compatible partial
  information is combined).
- `*-failN`: an **invalid** instance — normalization/validation fails, e.g.
  a key-constraint merge fails (non-unifiable formal attributes, placeholder
  `-` vs a concrete value), a uniqueness constraint (24–29) is violated, a
  mandatory argument is the placeholder `-`, or an impossibility constraint
  (e.g. 52) is violated.

`<category>` names the record type or rule family under test (`activity`,
`generation`, ..., `activity-start`/`activity-end` for Constraints 28/29,
`attributes-*` for attribute-combination cases, `bundle` for bundle scoping).

## Local quirks

- Each file begins with a `<?org.openprovenance.prov.xml ...?>` processing
  instruction instead of a standard XML declaration; XML parsers accept it.
- The three `bundle-*.xml` files wrap bundle contents in `<prov:bundle>`
  (ProvToolbox's dialect) where the W3C PROV-XML XSD (vendored under
  `src/prov/tests/schemas/`) defines `<prov:bundleContent>`; `prov` cannot
  parse them (issue [#254](https://github.com/trungdong/prov/issues/254)) and
  the test module skips them as parse failures.

Do not edit the `.xml` files; they are a vendored upstream corpus.
