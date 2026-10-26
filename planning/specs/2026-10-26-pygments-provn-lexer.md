# Release 3.3.0: the Pygments lexer for PROV-N (#628)

**Status:** In progress.

Written 2026-10-26 against `main` 35500e3. Spec 1 (`2026-10-20-release-3.3.0-design.md`,
section 2) had planned #628 from its issue alone; this file replaces that arrangement so
the design stays in the repository after the issue closes. The documentation rules every
page edit follows are section 3 of `2026-10-23-docs-restructure-design.md`.

## 1. Purpose

`prov` ships a Pygments lexer for PROV-N, registered under the `pygments.lexers` entry
point, so that every tool that asks Pygments for a language named `provn` highlights PROV-N
as soon as `prov` is installed, with no configuration in the consuming tool. The lexer is
written to be submitted to Pygments itself after one release in the wild, because that is
the only route to the audiences a plugin cannot reach (section 2.2). The ROADMAP's 3.3.0
row promises the lexer.

## 2. Evidence

### 2.1 What a plugin lexer reaches

Every Python tool below calls `pygments.lexers.get_lexer_by_name`, which checks Pygments'
own table and then loads the `pygments.lexers` entry points. So the lexer works the day the
PR merges in any environment that holds `prov`: `pygmentize` with all its formatters (HTML,
LaTeX, RTF, SVG, terminal), Sphinx and MyST (prov's own site: Read the Docs and the CI
`docs` job both `uv sync` the project, so the entry point is present), MkDocs and Material,
Pelican and Nikola, docutils, nbconvert's HTML and LaTeX export (a `%%provn` magic cell
needs one line, `c.HighlightMagicsPreprocessor.languages = {"%%provn": "provn"}`), the
`rich` terminal library, minted v2 with shell escape, and self-hosted Trac, Review Board
and Sourcehut.

### 2.2 What only an upstream lexer reaches

TeX Live 2025's minted v3 uses a bundled Pygments that cannot see plugins, and Overleaf
cannot pip install, so those users get PROV-N only once Pygments itself ships the lexer and
TeX Live picks it up. Pygments releases a feature version every 5 to 15 months (2.18 May
2024, 2.19 January 2025, 2.20 March 2026, 2.21 August 2026); 2.21 has no PROV-N lexer.
Chroma, the engine behind Hugo, Gitea and Forgejo, converts Pygments lexers with its
maintained `pygments2chroma_xml.py`, so an upstream lexer is also the input to that
audience. Upstream requires a self-contained module under `pygments/lexers` with `name`,
`aliases`, `filenames`, `mimetypes`, `url` and `version_added`, a regenerated
`_mapping.py`, and golden-token tests; "lexers which can't be tested will not be accepted".

### 2.3 What no Pygments lexer reaches

No code forge uses Pygments. GitHub uses Linguist with TextMate grammars and lists a
language only after 2,000 or more files in that language appear on GitHub in a year, so
GitHub highlighting is out of reach and a `provn` fence renders plain there, as `text` does
today. GitLab uses Rouge, pandoc and Quarto use KDE syntax XML, Docusaurus uses Prism,
Jupyter Book 2 uses highlight.js, JupyterLab's editor uses CodeMirror, and VS Code, Sublime
Text and Shiki-based sites use TextMate grammars. The 2014 `provn-textmate` bundle is a
TextMate 1 plist, last committed 2014-03-19, loadable by VS Code and Shiki after conversion
to JSON. The 2014 Ace mode is minified in the legacy ProvStore checkout. Each of these
audiences needs its own artefact (section 7).

### 2.4 Pygments facts that constrain the design

- `find_plugin_lexers` is a bare `entrypoint.load()` with no try/except. A plugin module
  that raises on import breaks every lookup that misses Pygments' own table, for any
  language.
- Pygments' own aliases are checked before plugins, so the entry point goes silent the day
  Pygments ships `provn`.
- `get_all_lexers`, `guess_lexer`, `pygmentize -L` and any by-name miss load every plugin
  module, so the module's import cost is paid often. The floor is `prov/__init__`, about
  8 ms; `prov.identifier` on top brings it to about 15 ms.
- Sphinx wraps every lexer in `raiseonerror`, so one `Error` token on valid input fails a
  `-W` build, which is how prov's docs are built.
- Pygments ships no `py.typed`. `types-Pygments` (typeshed) types every lexer class
  attribute as a class variable, so `name`, `aliases`, `filenames`, `mimetypes`, `url`,
  `version_added` and `tokens` need no annotations under `mypy --strict`, and `words`,
  `include` and `default` pass; `bygroups` alone is untyped (`no-untyped-call`). A module
  named `prov/pygments.py` resolves its inner `import pygments` to the real package at
  runtime and under mypy (probed 2026-10-26).
- Pytest requires Pygments, so every prov test environment already holds it, including the
  minimal-install worktree (`uv sync --locked --group dev`). PyPI's README renderer emits
  `<pre lang="provn">` plain for an unknown language (probed with `readme_renderer[md]`).

### 2.5 The 2014 grammars

Both 2014 grammars coloured the expression name apart from identifiers and only before
`(`, split a qualified name into prefix, `:` and local part, coloured attribute keys apart
from values, and tokenised `prefix` and `default` declarations as a unit. Ace alone gave
the unquoted `xsd:dateTime` and the `-` marker their own tokens. Both were wrong where
the tokenizer is right: `document` anchored to the file start, bundle names requiring a
prefix, no statements after a bundle, no `\:` or `%XX` escapes, no `"""` long strings, no
`@lang` tags, no `;` after an identifier, ASCII-only names.

### 2.6 The docs today

Six PROV-N blocks are fenced `text`: `docs/tutorial/getting-started.md` lines 60 and 137
and `docs/explanation/unification-flattening.md` lines 38, 57, 111 and 128, plus
`README.md` lines 38 to 46. A grep for `text` fences whose first line is a PROV-N token
found no others; the PROV-N in `docs/howto/provn.md` sits inside Python strings in `python`
fences. `docs/conf.py` sets no `highlight_language` and no `pygments_style`.

## 3. Design

### 3.1 Module and registration

The lexer is `ProvNLexer` in `prov/pygments.py`, the module named after its extra as
`prov.dot` and `prov.graph` are. The module exports that one name, but the class is not
part of prov's public API. Callers reach it by name, through
`pygments.lexers.get_lexer_by_name("provn")`, and pass it to Pygments' own `highlight`. It
has no reference page and no entry in `test_public_api.py`, so retiring it (3.5) removes
nothing a documented caller relies on. The lexer defines no `analyse_text`, so
`guess_lexer` never picks it on content alone. The module imports Pygments and nothing
else, so a
plugin load pays only the `prov/__init__` floor (2.4), and it imports cleanly whenever
Pygments is present, because a failing plugin breaks Pygments. When Pygments is absent the
import raises `ModuleNotFoundError` naming the `pygments` extra in the pattern of `dot.py`
and `graph.py`; that path is reached only by a direct import, since nothing loads the entry
point without Pygments.

`pyproject.toml` gains the extra `pygments = ["pygments>=2.18"]` with no upper bound (the
floor verified by a probe during the build), the entry point
`[project.entry-points."pygments.lexers"] provn = "prov.pygments:ProvNLexer"`, and
`types-Pygments` in the dev group, with `uv.lock` regenerated because CI syncs
`--locked`. `bygroups` is untyped in the stubs, so the module wraps
it once in a typed one-line helper that carries the single `no-untyped-call` ignore, and
the grammar calls the helper. A `[[tool.mypy.overrides]]` entry is not an option, because
`test_mypy_override_list_only_shrinks` asserts the block holds exactly one entry, the
shrinking list of test modules. `docs/dependencies.md` explains both pins.

Lookup metadata: `name = "PROV-N"`, `aliases = ["provn", "prov-n"]`,
`filenames = ["*.provn"]`, `mimetypes = ["text/provenance-notation"]` (the IANA-registered
type the Recommendation names), `url = "https://www.w3.org/TR/prov-n/"`.

### 3.2 A self-contained lexer

`ProvNLexer` is a `RegexLexer` that carries its own copies of the five strings the PROV-N
tokenizer imports from `prov.identifier` (`_NCNAME_START_CHARS`, `_PN_CHARS`,
`_PN_CHARS_ESC`, `_PN_CHARS_OTHER`, `_PN_PREFIX`) and its own keyword list. The copies
hold the source values written out in full, since `prov.identifier` derives `_PN_CHARS`
from another class. `_PN_PREFIX` is a regex fragment that already holds its brackets, and
the other four are class bodies. The lexer passes `_PN_CHARS_ESC` and `_PN_CHARS_OTHER`
through `re.escape`, as the tokenizer does. A test pins the copies to their sources, so
drift fails CI (section 5). Importing them
instead would make the upstream copy a different file and put `prov.identifier` on every
plugin load. The upstream submission is this file minus the import guard, with
`version_added` filled in.

The lexer follows the tokenizer's rules, not the 2014 grammars': `document` may follow a
comment, a bundle name may be bare, statements may follow a bundle, local names take `\:`
and `%XX` escapes and the dot rule, strings may be `"""` long strings with line breaks,
`@lang` follows a string only, `;` follows an identifier, `{ }` tuples and nested calls
are the #520 extensibility form PR 23 (#681) added to the parser, and names are Unicode.
An unknown name before `(` lexes as an extensibility expression, never as `Error`. The
lexer never emits `Error` on input the PROV-N reader accepts (2.4, Sphinx).

The reader reserves no word. With a default namespace declared it accepts
`entity(bundle)`, `[prefix="x"]` and `bundle bundle`. So `document`, `endDocument`,
`bundle`, `endBundle`, `prefix` and `default` are keywords only outside brackets, and the
name that follows `bundle` is a name. Inside `( )` and `[ ]` the six words lex as names or
attribute keys.

### 3.3 Token mapping

| Construct | Token |
|---|---|
| `document`, `endDocument`, `bundle`, `endBundle`, outside brackets | `Keyword` |
| `prefix`, `default`, outside brackets | `Keyword.Declaration` |
| the declared name in `prefix ex <iri>` | `Name.Namespace` |
| the 17 bare expression names, bare `mentionOf` and `prov:mentionOf`, before `(` | `Keyword` |
| any other name before `(` (extensibility, #520) | `Name.Function` |
| prefix of a qualified name | `Name.Namespace`; the `:` `Punctuation`; the local part `Name` or its construct's class |
| attribute key before `=`, the five `prov:` reserved keys included | `Name.Attribute` |
| `<iri>` | `String.Other` |
| `"..."`, `"""..."""` | `String.Double` |
| `'prefix:local'` | `String.Single` |
| `%%` | `Operator`; the datatype name `Keyword.Type` |
| `@en` | `Name.Decorator` |
| unquoted `xsd:dateTime` | `Literal.Date` |
| integers, `-4` | `Number.Integer` |
| `-` marker | `Keyword.Constant` |
| `//`, `/* */` | `Comment.Single`, `Comment.Multiline` |
| `( ) [ ] { } , ; =` | `Punctuation` |
| whitespace | `Whitespace` |

A qualified name always lexes as three tokens, as both 2014 grammars split it (2.5). The
prefix is `Name.Namespace` and the `:` is `Punctuation` wherever the name stands. The local
part takes the class of the construct's row. So `prov:mentionOf(` lexes as
`Name.Namespace`, `Punctuation`, `Keyword`, an extensibility call `ex:foo(` ends in
`Name.Function`, `prov:type=` ends in `Name.Attribute`, and `xsd:string` after `%%` ends in
`Keyword.Type`. A quoted `'prefix:local'` stays one `String.Single` token.

Bare `mentionOf` is a keyword although the strict profile rejects it; highlighting is
lenient by nature and the default profile accepts it. The reserved attribute keys take the
same class as any key; a separate class would be a second list to pin against the model.

### 3.4 Docs and README

The six `text` fences of 2.6 and the README block become `provn` in the same PR as the
lexer, because a `provn` fence before the lexer exists fails `sphinx-build -W`, and the
README switch costs nothing where no lexer is present. The PROV-N how-to gains a "Syntax
highlighting" section: the lexer registers itself once prov is installed; one `pygmentize`
command; the `get_lexer_by_name("provn")` call for Python callers; Sphinx, MkDocs and Pelican find it with no configuration; the one nbconvert line
for `%%provn` cells; and two sentences on LaTeX, that `pygmentize -f latex` and minted v2
work now and that TeX Live's bundled minted v3 and Overleaf wait for the lexer to ship in
Pygments itself. HISTORY records the lexer under 3.3.0 in the usual form.

### 3.5 Upstream and retirement

After one prov release carries the lexer, it is submitted to Pygments as a copy of the
module with the import guard removed and `version_added` set, with golden-token tests in
Pygments' format. Once a Pygments release carries it, prov drops the entry point and
`prov/pygments.py` in its next minor release and raises the extra's floor to that Pygments
version, so `prov[pygments]` keeps meaning "PROV-N highlighting works". A minor release
may drop the module because the class was never public API (3.1). Keeping both would
be harmless at runtime, since Pygments' own alias shadows the plugin, but it is dead code
and a second copy to maintain.

## 4. Sequence

| PR | Issue | Depends on | Cut rule |
|---|---|---|---|
| 25a | #628 | `main` at any point before the 3.3.0 freeze (spec 1, section 2); nothing in spec 3 | Drops whole; #628 leaves the milestone; nothing depends on it |

One PR. It touches no module spec 3's PRs edited, so it needs no ordering against them. It
runs the repository's pre-PR review without the bug-and-security pass, because it changes
no reader. It runs the A/B against `main` for the record; nothing it adds is on an
assertion or serialisation path. The follow-on issues of section 7 are filed when the PR is
planned, not built.

## 5. Tests

- Every document in `examples.py`, serialised to PROV-N, and every `.provn` under
  `src/prov/tests/` that `prov.read(format="provn")` accepts, lexes with no `Error` token.
  The reader is the oracle for "well-formed"; a fixture it rejects may lex with `Error`.
- One rich fixture (`fixtures/written-by-3.2.3/primer.provn` or `attribute-values.provn`)
  has an exact `(token, value)` table for the constructs of 3.3, and a hand-written snippet
  covers `"""`, `\:`, `%XX`, `@lang`, `;`, `{ }` and an extensibility expression, since no
  fixture holds them.
- The joined token values reproduce the input character for character, which Pygments
  requires. Pygments' defaults strip leading and trailing newlines and add one at the end.
  Ten fixtures under `written-by-3.2.3/`, `primer.provn` and `attribute-values.provn` among
  them, end in `endDocument ` with no newline, and six files start with a blank line. So
  every test builds the lexer with
  `stripnl=False, ensurenl=False` and compares against the raw text. Pygments also turns
  CRLF into LF and strips a BOM whatever the options, and the test tree holds neither.
- The lexer's bare keyword set equals the unprefixed keys of the parser's `_KEYWORDS` (the
  17 expression names) plus `mentionOf`, which the parser accepts without a key. The
  `("prov", "mentionOf")` key of `_KEYWORDS` is checked separately. The lexer's copied
  strings equal `prov.identifier`'s.
- `get_lexer_by_name("provn")` resolves through the entry point.
- `import prov` leaves `pygments` out of `sys.modules`.
- One subprocess test hides Pygments (`sys.modules["pygments"] = None`) and asserts the
  `ModuleNotFoundError` names `prov[pygments]`, since no environment lacks Pygments. It
  matches the message, because the exception's `name` reads `pygments.lexer` under this
  way of hiding the package.
- The gates are unchanged: pytest brings Pygments into every environment, so the
  interpreter loop and CI need no new extra.

## 6. Documentation and changelog

Section 3.4. `CLAUDE.md`'s setup section lists the new extra beside the others; the gate
commands do not change. `docs/dependencies.md` gains the two pins.

## 7. Out of scope and follow-on issues

Out of #628: a PROV-N formatter, lexers for the other formats, the nbconvert magic itself,
and every artefact of 2.3. Three issues follow, each its own work:

- `provn-textmate`: a refreshed grammar as `.tmLanguage.json` plus a VS Code extension,
  serving VS Code, Sublime Text and Shiki sites. Chroma and the pandoc KDE XML wait until
  after the upstream submission.
- `prov`: coloured PROV-N from `prov-convert` on a TTY through the same lexer and
  Pygments' terminal formatter, when Pygments is present, no milestone.
- `prov`: adopting the 215 probes of `prov-corpus` with their `expected.tsv` accept-or-
  reject outcomes per profile into the test tree, which holds 534 of the corpus's 739
  PROV-N files today, no milestone.
