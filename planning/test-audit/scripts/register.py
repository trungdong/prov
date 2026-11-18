"""Keep the register of standing test-audit rulings.

`register/<module>.tsv` holds one ruling for each test function of a module. `stamp`
records the fingerprint of each function once its ruling is final. `check` sorts every
function into unchanged, changed, new, source moved and gone, so that a later audit
judges only what is not unchanged. A row that a later layer ruled (`ruled_by` is not
`classifier`), `removed` rows included, is source moved when a backticked `src/prov`
definition or a sibling test (`test_x.py::test_y`) named in its reason changed since its
audit commit. `check --names` prints what each such row follows. A reason that opens, or
opens a sentence, with `Later audit:` is listed after the groups, and so are the
`rewrite` and `query` rows. `draft` turns the classifier's `keep` and `protected` ledger
rows into register rows. The format is in `rubric.md` (The register).

    python planning/test-audit/scripts/register.py stamp test_json
    python planning/test-audit/scripts/register.py check [--list | --names] [test_json ...]
    python planning/test-audit/scripts/register.py draft test_json ledger.md
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import functools
import hashlib
import re
import subprocess  # nosec B404
import sys
from collections import Counter, defaultdict
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, NoReturn

ROOT = Path(__file__).resolve().parents[3]
TESTS = ROOT / "src/prov/tests"
REGISTER = ROOT / "planning/test-audit/register"
SOURCE = "src/prov"
ALLOWED = {
    "ruling": (
        "keep",
        "merged",
        "narrowed",
        "rewrite",
        "query",
        "protected",
        "removed",
    ),
    "ruled_by": ("classifier", "judge", "maintainer"),
    "confidence": ("high", "medium", "low", "-"),
}
GROUPS = ("unchanged", "changed", "new", "source moved", "gone")
Def = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")
SIBLING = re.compile(r"\b(test_\w+)\.py::(\w+)")
LEDGER = ["Test", "Items", "Pins", "Reason", "Sibling", "Verdict", "Confidence", "Note"]
DRAFTED = ("keep", "protected")
LATER = re.compile(r"(?:^|[.!?][)\"']?\s+)Later audit:")


@dataclasses.dataclass
class Row:
    function: str
    ruling: str
    ruled_by: str
    confidence: str
    audit_commit: str
    fingerprint: str
    reason: str


class Found(NamedTuple):
    function: str
    group: str
    note: str = ""
    later: bool = False
    ruling: str = ""


COLUMNS = tuple(f.name for f in dataclasses.fields(Row))


def fail(message: str) -> NoReturn:
    raise SystemExit(message)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # nosec B603 B607 - nosemgrep
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        text=True,
        errors="replace",
    )


@functools.cache
def in_history(commit: str) -> bool:
    """Say whether the commit is HEAD or one of its ancestors."""
    return git("merge-base", "--is-ancestor", commit, "HEAD").returncode == 0


def span_text(lines: list[str], node: Def) -> str:
    """Return the node's source from its first decorator to its last line."""
    start = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return "\n".join(line.rstrip() for line in lines[start - 1 : node.end_lineno])


def module_path(module: str) -> Path:
    path = TESTS / f"{module}.py"
    return path if path.is_file() else fail(f"{path}: no such test module")


def test_sources(path: Path) -> dict[str, str]:
    """Map each module-level test function to its source text."""
    return test_texts(path.read_text())


def test_texts(text: str) -> dict[str, str]:
    """Map each module-level test function in a module's text to its source text."""
    lines = text.splitlines()
    return {
        node.name: span_text(lines, node)
        for node in ast.parse(text).body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name.startswith("test_")
    }


def collect_ids(path: Path) -> dict[str, list[str]]:
    """Map each test function to its sorted collected item ids."""
    rel = path.relative_to(ROOT).as_posix()
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    proc = subprocess.run(  # nosec B603 - nosemgrep
        [*command, "-p", "no:cacheprovider", rel],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(proc.stdout + proc.stderr)
    ids: dict[str, list[str]] = defaultdict(list)
    for line in proc.stdout.splitlines():
        if line.startswith(f"{rel}::"):
            ids[line.split("[", 1)[0].rsplit("::", 1)[-1]].append(line)
    return {name: sorted(items) for name, items in ids.items()}


def fingerprint(source: str, ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join([source, *sorted(ids)]).encode()).hexdigest()[:16]


def validate(row: Row, where: str) -> None:
    for column, value in zip(COLUMNS, dataclasses.astuple(row), strict=True):
        if any(c in value for c in "\t\r\n"):
            fail(f"{where}: {column} holds a tab or a newline")
        if column in ALLOWED and value not in ALLOWED[column]:
            fail(f"{where}: {column} {value!r} is not one of {ALLOWED[column]}")


def read_register(path: Path) -> dict[str, Row]:
    lines = path.read_text().splitlines()
    if lines[:1] != ["\t".join(COLUMNS)]:
        fail(f"{path}: row 1: the header must be {', '.join(COLUMNS)} (tab separated)")
    rows: dict[str, Row] = {}
    for number, line in enumerate(lines[1:], start=2):
        fields = line.split("\t")
        if len(fields) != len(COLUMNS):
            fail(
                f"{path}: row {number}: found {len(fields)} columns, not {len(COLUMNS)}"
            )
        row = Row(*fields)
        validate(row, f"{path}: row {number}")
        if rows.setdefault(row.function, row) is not row:
            fail(f"{path}: row {number}: {row.function} appears twice")
    return rows


def write_register(path: Path, rows: dict[str, Row]) -> None:
    lines = ["\t".join(COLUMNS)]
    for name in sorted(rows):
        validate(rows[name], f"{path}: {name}")
        lines.append("\t".join(dataclasses.astuple(rows[name])))
    path.write_text("\n".join(lines) + "\n")


def stamp_problems(
    rows: dict[str, Row], sources: dict[str, str]
) -> dict[str, list[str]]:
    """Return the functions with no row, the rows with no function and the removed
    rows whose function still exists."""
    return {
        "functions with no row": sorted(set(sources) - set(rows)),
        "rows with no function": sorted(
            n for n, r in rows.items() if r.ruling != "removed" and n not in sources
        ),
        "removed rows whose function exists": sorted(
            n for n, r in rows.items() if r.ruling == "removed" and n in sources
        ),
    }


def cmd_stamp(module: str) -> None:
    path, register = module_path(module), REGISTER / f"{module}.tsv"
    if not register.is_file():
        fail(f"{register}: no register file; write one before you stamp")
    rows, sources = read_register(register), test_sources(path)
    problems = stamp_problems(rows, sources)
    if any(problems.values()):
        fail("\n".join([str(register), *(f"{k}: {v}" for k, v in problems.items())]))
    ids, head = collect_ids(path), git("rev-parse", "--short=12", "HEAD").stdout.strip()
    stamped = current = 0
    for name, row in rows.items():
        if row.ruling == "removed":
            if row.fingerprint or not in_history(row.audit_commit):
                row.fingerprint, row.audit_commit = "", head
                stamped += 1
            continue
        new = fingerprint(sources[name], ids.get(name, []))

        # A rebase leaves a row pointing at a commit outside the branch's history,
        # which a fresh clone does not hold. Such a row is stamped again.

        if row.fingerprint == new and in_history(row.audit_commit):
            current += 1
        else:
            row.fingerprint, row.audit_commit = new, head
            stamped += 1
    write_register(register, rows)
    print(f"{module}: {stamped} rows stamped, {current} already current")


Digests = dict[tuple[str, str], str]


def is_source(path: str) -> bool:
    """Say whether a repository path is a Python file of the package, not its tests."""
    return path.endswith(".py") and not path.startswith(f"{SOURCE}/tests/")


def definitions(files: dict[str, str]) -> Digests:
    """Map (path, qualified name) to a source hash for every def and class."""
    texts: defaultdict[tuple[str, str], list[bytes]] = defaultdict(list)

    def walk(node: ast.AST, prefix: str, path: str, lines: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, Def):
                qual = f"{prefix}{child.name}"
                texts[path, qual].append(span_text(lines, child).encode())
                walk(child, f"{qual}.", path, lines)
            else:
                walk(child, prefix, path, lines)

    for path, text in files.items():
        if is_source(path):
            walk(ast.parse(text), "", path, text.splitlines())

    # Definitions that share a name (an overload group) hash together in file order.

    return {k: hashlib.sha256(b"\0".join(v)).hexdigest() for k, v in texts.items()}


def tree_definitions() -> Digests:
    paths = (ROOT / SOURCE).rglob("*.py")
    return definitions({p.relative_to(ROOT).as_posix(): p.read_text() for p in paths})


def commit_definitions(commit: str) -> Digests | None:
    """Return the definitions at a commit, or None when git cannot resolve it."""
    listing = git("ls-tree", "-r", "--name-only", commit, SOURCE)
    if listing.returncode != 0:
        return None
    names = [n for n in listing.stdout.splitlines() if is_source(n)]
    return definitions({n: git("show", f"{commit}:{n}").stdout for n in names})


def named_tokens(reason: str) -> list[list[str]]:
    """Return the backticked Python names in a reason, split on dots."""
    found = (t.strip().removesuffix("()") for t in re.findall(r"`([^`]+)`", reason))
    return [t.split(".") for t in found if NAME.fullmatch(t)]


def named(defs: Digests, tokens: list[list[str]]) -> Digests:
    """Keep the definitions whose trailing name components equal a token."""
    return {
        key: digest
        for key, digest in defs.items()
        for parts in tokens
        if key[1].split(".")[-len(parts) :] == parts
    }


@functools.cache
def read_tests(commit: str, module: str) -> dict[str, str]:
    """Map a test module's functions to source at a commit ("" for the work tree)."""
    if commit:
        shown = git("show", f"{commit}:{SOURCE}/tests/{module}.py")
        return test_texts(shown.stdout if shown.returncode == 0 else "")
    path = TESTS / f"{module}.py"
    return test_sources(path) if path.is_file() else {}


class Audit:
    """Classify test functions against a register, reading each commit once."""

    def __init__(self) -> None:
        self.now = tree_definitions()
        self.before: dict[str, Digests | None] = {}

    def moved_defs(self, row: Row, old: Digests) -> set[str]:
        """Name the definitions in the reason that differ from the audit commit."""
        tokens = named_tokens(row.reason)
        was, now = named(old, tokens), named(self.now, tokens)
        if set(was.values()) == set(now.values()):
            return set()
        return {k[1] for k in was.keys() | now.keys() if was.get(k) != now.get(k)}

    def moved_siblings(self, module: str, row: Row) -> set[str]:
        """Name the sibling tests in the reason that differ from the audit commit."""
        moved = set()
        for other, name in set(SIBLING.findall(row.reason)):
            if (other, name) == (module, row.function):
                continue
            was = read_tests(row.audit_commit, other).get(name)
            if was is not None and was != read_tests("", other).get(name):
                moved.add(f"{other}.py::{name}")
        return moved

    def moved(self, module: str, row: Row, old: Digests) -> str:
        """Name the definitions and sibling tests that moved since the audit commit."""
        names = self.moved_defs(row, old) | self.moved_siblings(module, row)
        return ", ".join(sorted(names))

    def followed(self, module: str, row: Row) -> str | None:
        """Name what a later layer's row follows that moved, or None for a lost commit.

        A classifier row follows nothing, so it gives "" once its commit resolves.
        """
        if row.audit_commit not in self.before:
            self.before[row.audit_commit] = commit_definitions(row.audit_commit)
        old = self.before[row.audit_commit]
        if old is None:
            return None
        return "" if row.ruled_by == "classifier" else self.moved(module, row, old)

    def classify_removed(self, module: str, row: Row) -> Found:
        """Classify a removed row whose function is absent."""
        names = self.followed(module, row)
        if names is None:
            return Found(row.function, "source moved", "unknown audit commit")
        return Found(row.function, "source moved" if names else "removed", names)

    def row_names(self, module: str, row: Row) -> list[str]:
        """List the definitions and sibling tests that a row's reason follows, and
        each backticked name that matches no definition."""
        tokens = named_tokens(row.reason)
        lines = sorted(f"  {path}::{qual}" for path, qual in named(self.now, tokens))
        missing = {".".join(parts) for parts in tokens if not named(self.now, [parts])}
        lines += [f"  {name} (matches nothing)" for name in sorted(missing)]
        for other, name in sorted(set(SIBLING.findall(row.reason))):
            if (other, name) != (module, row.function):
                gap = "" if name in read_tests("", other) else " (no such test)"
                lines.append(f"  {other}.py::{name}{gap}")
        return [f"{module}::{row.function}", *(lines or ["  nothing"])]

    def classify(
        self, module: str, name: str, row: Row | None, source: str, ids: Sequence[str]
    ) -> Found:
        if row is None:
            return Found(name, "new")
        if row.ruling == "removed":
            return Found(name, "changed", "ruled removed but the function exists")
        if row.fingerprint != fingerprint(source, ids):
            return Found(name, "changed")
        names = self.followed(module, row)
        if names is None:
            return Found(name, "changed", "unknown audit commit")
        return Found(name, "source moved", names) if names else Found(name, "unchanged")


def check_module(audit: Audit, module: str) -> list[Found]:
    """Return one finding for each test function and each row without a function."""
    path, register = TESTS / f"{module}.py", REGISTER / f"{module}.tsv"
    if not register.is_file():
        return [
            Found(name, "not audited") for name in test_sources(module_path(module))
        ]

    # A test module that no longer exists leaves only rows without a function.

    sources = read_tests("", module)
    ids = collect_ids(path) if sources else {}
    rows = read_register(register)
    found = [
        audit.classify(module, name, rows.get(name), source, ids.get(name, []))
        for name, source in sources.items()
    ]
    for name, row in rows.items():
        if name not in sources:
            found.append(
                audit.classify_removed(module, row)
                if row.ruling == "removed"
                else Found(name, "gone")
            )
    return [annotate(f, rows) for f in found]


def annotate(f: Found, rows: dict[str, Row]) -> Found:
    """Record a finding's ruling and whether its reason holds a later audit's note."""
    row = rows.get(f.function)
    if row is None:
        return f
    return f._replace(later=bool(LATER.search(row.reason)), ruling=row.ruling)


def print_report(results: dict[str, list[Found]]) -> None:
    audited = {m: f for m, f in results.items() if f and f[0].group != "not audited"}
    for module, found in results.items():
        if module not in audited:
            print(f"{module}: not audited ({len(found)} functions)")
    if audited:
        print(f"{'module':<32}" + "".join(f"{g:>14}" for g in GROUPS))
    for module, found in audited.items():
        counts = [sum(f.group == g for f in found) for g in GROUPS]
        print(f"{module:<32}" + "".join(f"{c:>14}" for c in counts))
    for group in GROUPS[1:]:
        print_group(group, audited)
    print_later(audited)
    print_rewrites(audited)


def print_group(group: str, audited: dict[str, list[Found]]) -> None:
    hits = [(m, f) for m, found in audited.items() for f in found if f.group == group]
    if hits:
        print(f"\n{group} ({len(hits)})")
    for module, f in hits:
        print(f"  {module}::{f.function}" + (f"  {f.note}" if f.note else ""))


def print_later(audited: dict[str, list[Found]]) -> None:
    """List the rows whose reason holds a later audit's note."""
    hits = [f"{m}::{f.function}" for m, fs in audited.items() for f in fs if f.later]
    if hits:
        print(f"\nlater audit ({len(hits)})")
    for hit in hits:
        print(f"  {hit}")


def print_rewrites(audited: dict[str, list[Found]]) -> None:
    """List the rows whose ruling is rewrite or query."""
    hits = [
        f"  {m}::{f.function}  {f.ruling}"
        for m, fs in audited.items()
        for f in fs
        if f.ruling in ("rewrite", "query")
    ]
    if hits:
        print(f"\nrewrite and query ({len(hits)})")
    for hit in hits:
        print(hit)


def print_names(audit: Audit, modules: list[str]) -> None:
    """Print what each row of a later layer follows, one block for each row."""
    for module in modules:
        register = REGISTER / f"{module}.tsv"
        rows = read_register(register).values() if register.is_file() else []
        for row in rows:
            if row.ruled_by != "classifier":
                print("\n".join(audit.row_names(module, row)))


def cmd_check(modules: list[str], list_only: bool, names_only: bool) -> None:
    names = modules or sorted(
        {p.stem for p in TESTS.glob("test_*.py")}
        | {p.stem for p in REGISTER.glob("test_*.tsv")}
    )
    audit = Audit()
    if names_only:
        return print_names(audit, names)
    results = {m: check_module(audit, m) for m in names}
    if not list_only:
        return print_report(results)
    for module, found in results.items():
        for f in found:
            print(f"{module}::{f.function}\t{f.group}")


def ledger_rows(path: Path) -> list[list[str]]:
    """Return the cells of each data row of the ledger table that has the LEDGER header.

    The Test, Verdict and Confidence cells lose any backticks around them.
    """
    lines = path.read_text().splitlines()
    heads = [i for i, line in enumerate(lines) if ledger_cells(line) == LEDGER]
    if not heads:
        fail(f"{path}: no table with the header {' | '.join(LEDGER)}")
    rows: list[list[str]] = []
    for number in range(heads[0] + 2, len(lines)):
        if not lines[number].strip().startswith("|"):
            break
        cells = ledger_cells(lines[number])
        if len(cells) != len(LEDGER):
            fail(
                f"{path}: line {number + 1}: found {len(cells)} cells, not {len(LEDGER)}"
            )
        rows.append(
            [c.strip("`") if i in (0, 5, 6) else c for i, c in enumerate(cells)]
        )
    return unique(path, rows)


def unique(path: Path, rows: list[list[str]]) -> list[list[str]]:
    """Return the ledger rows, or fail naming each test that has more than one."""
    counts = Counter(row[0] for row in rows)
    twice = sorted(name for name, count in counts.items() if count > 1)
    if twice:
        fail(f"{path}: more than one row for {', '.join(twice)}")
    return rows


def ledger_cells(line: str) -> list[str]:
    """Split a table line on its unescaped pipes and strip each cell."""
    pieces = re.split(r"(?<!\\)\|", line.strip())[1:-1]
    return [cell.strip().replace("\\|", "|") for cell in pieces]


def draft_row(cells: list[str]) -> Row:
    """Turn a keep or protected ledger row into a register row."""
    _, _, pins, reason, _, verdict, confidence, _ = cells
    text = pins if reason in ("", "-") else f"{pins} {reason}"
    return Row(cells[0], verdict, "classifier", confidence, "", "", text)


def listed(count: int, label: str, names: list[str]) -> str:
    return f"{count} {label}" + (f" ({', '.join(names)})" if names else "")


def cmd_draft(module: str, ledger: Path) -> None:
    sources, cells = test_sources(module_path(module)), ledger_rows(ledger)

    # A test that a later layer removed or folded in has left the module, so its
    # ledger row is left for that layer, like a row with any other verdict.

    drafts = [draft_row(c) for c in cells if c[5] in DRAFTED and c[0] in sources]
    left = [c[0] for c in cells if c[5] not in DRAFTED or c[0] not in sources]
    register = REGISTER / f"{module}.tsv"
    rows = read_register(register) if register.is_file() else {}
    kept = [
        d.function for d in drafts if rows.get(d.function, d).ruled_by != "classifier"
    ]
    rows.update({d.function: d for d in drafts if d.function not in kept})
    write_register(register, rows)
    print(
        f"{module}: {len(drafts) - len(kept)} rows drafted, "
        f"{listed(len(left), 'left for a later layer', left)}, "
        f"{listed(len(kept), 'kept as ruled', kept)}"
    )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    stamp = commands.add_parser("stamp", help="fingerprint a module's register rows")
    stamp.add_argument("module")
    check = commands.add_parser("check", help="sort the tests by audit state")
    check.add_argument("modules", nargs="*")
    mode = check.add_mutually_exclusive_group()
    mode.add_argument(
        "--list", action="store_true", help="print only function and group"
    )
    mode.add_argument(
        "--names",
        action="store_true",
        help="print what each later-layer row follows",
    )
    draft = commands.add_parser("draft", help="draft register rows from a ledger")
    draft.add_argument("module")
    draft.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    if args.command == "stamp":
        cmd_stamp(args.module.removesuffix(".py"))
    elif args.command == "draft":
        cmd_draft(args.module.removesuffix(".py"), args.ledger)
    else:
        cmd_check([m.removesuffix(".py") for m in args.modules], args.list, args.names)


if __name__ == "__main__":
    main()
