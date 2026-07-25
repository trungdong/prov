# PROV-CONSTRAINTS unification corpus

153 PROV-XML documents exercising the W3C PROV-CONSTRAINTS unification and
key-constraint rules, consumed by
`src/prov/tests/test_unification_constraints.py`, which characterizes
`unified()` against the PROV-CONSTRAINTS rework landed in 3.0 (umbrella issue
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

## W3C type-compatibility corpus (`.provx`)

Seven additional PROV-XML documents (`type-*.provx`), exercising the
same-identifier type-compatibility rules (Constraints 50, 53–56 — `prov`
implements 53/54/55 only; see "Naming convention" below) that the
ProvToolbox corpus above does not cover at all, consumed by
`test_unification_constraints.py`'s W3C-corpus characterization
(`test_w3c_type_compatibility_characterization`).

### Origin

Fetched verbatim (retrieved 2026-07-25) from the W3C Provenance Working
Group's test case repository, listed in its manifest
(`https://dvcs.w3.org/hg/prov/raw-file/default/testcases/all-tests.txt`):

```
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-collection-FAIL-c56.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-f1-FAIL-c50-c55.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-f2-FAIL-c50-c55.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-f3-FAIL-c54.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-f4-FAIL-c53.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-s1-PASS-c50-c55.provx
https://dvcs.w3.org/hg/prov/raw-file/default/testcases/constraints/type-s2-PASS-c50-c55.provx
```

The directory also carries paired `.ttl` (Turtle/PROV-O) and `.provn`
siblings for each case; only the `.provx` (PROV-XML) files are vendored
here, matching the ProvToolbox corpus's XML-only policy above.

### Licence

W3C publishes its test suites under a choice of two licences (see
<https://www.w3.org/copyright/test-suites-licenses/>): the **W3C test suite
license** (2008 version,
<https://www.w3.org/Consortium/Legal/2008/04-testsuite-license.html>) or a
**3-clause BSD license**, "for software development, bug tracking, and other
applications that do not require assertions of performance to the public or
implied claims of conformance to a W3C Specification" — exactly this use.
The W3C test suite license permits copying and distribution "in any medium
for any purpose and without fee or royalty" provided the original document's
URL and copyright notice are retained:

> Copyright © [$date-of-document] World Wide Web Consortium, (MIT, ERCIM,
> Keio, Beihang) and others. All Rights Reserved.
> <https://www.w3.org/copyright/test-suites-licenses/>

Both licences permit verbatim vendoring for a non-branded, internal test
corpus such as this one.

### Naming convention

These files use the W3C corpus's own convention, distinct from ProvToolbox's
`-successN`/`-failN`: `type-<case>-PASS-c<NN[,-c<MM>...]>.provx` /
`type-<case>-FAIL-c<NN[,-c<MM>...]>.provx`, where the suffix lists every
constraint the case was designed to probe. Note that a `FAIL` case is the
W3C Working Group's own claim about the case's validity against the *full*
specification (constraint numbering it cites, including 50 and 56, that
`unified()` does not implement) — it is not a claim that `prov`'s `unified()`
must raise on it; see the per-case outcome table in
`test_unification_constraints.py`'s docstring.

### Local quirks

- `type-f2-FAIL-c50-c55.provx` is invalid only via Constraint 50's
  typing inference (an id used in a `wasGeneratedBy`'s `activity` role is
  thereby inferred to have type `activity`, clashing with its asserted
  `entity` type) — `unified()` does not perform that inference (it compares
  only explicitly-asserted record types), so this case does not raise here.
- `type-collection-FAIL-c56.provx` tests Constraint 56 (empty-collection
  membership), which `unified()` does not implement at all.

Do not edit the `.provx` files; they are a vendored upstream corpus.
