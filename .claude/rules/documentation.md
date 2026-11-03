# Documentation rules

These rules govern every change to a page under `docs/`, a README or a docstring.

Every pull request that touches a page or a docstring follows these rules.

1. Open each page and each section with what most readers need. Put a rare case in the
   docstring, on the conformance page or in an "Edge cases" section at the bottom of the page.
2. Give each fact one home, and link to it from every other page. The table below lists the
   homes.
3. Keep release history in `HISTORY.md`, `docs/whats-new-3.md`, `docs/upgrading-3.0.md` and the
   3.3.0 upgrade guide (`docs/howto/prepare-for-3-3.md`). Elsewhere write no "since X.Y", no
   "3.2.0 added" and no benchmark percentage. A `deprecated` directive, and a compatibility
   statement that names the release it protects, keep their version.
4. Write nothing that dates. State no measured figure tied to a machine or an interpreter and
   no date that will pass, apart from the dates in the support policy, the per-release
   conformance sentence and the measured figures in `benchmarks/README.md`.
5. Link to a specification and do not cite its clause numbers. Only `conformance.md` and
   code comments cite a section number.
6. Outside the pages rule 3 names, link an issue only for an open limitation or a decision a
   reader may want to follow. Never link one to record the history of a fix. A code comment
   keeps an issue number that explains why a guard exists.
7. Change no behaviour in a documentation change. Correct a sentence that is wrong against
   the code, never the code to match the sentence, and list the correction in the pull
   request body.

| Fact | Home |
|---|---|
| Extras | `docs/installation.md` |
| Auto-detection | `docs/howto/read-write.md` |
| Format limitations | `docs/reference/conformance.md` |
| Supported release lines | `SECURITY.md` |
| Python-version policy | `ROADMAP.md` |
| Gate commands | `CONTRIBUTING.md` |
| Python floor and what pip installs below it | `docs/installation.md` |
| Equality rules and Python values | `docs/reference/values.md` |
| Exceptions | `docs/reference/serializers.md` |
