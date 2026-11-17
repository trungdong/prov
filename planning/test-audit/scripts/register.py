"""Keep the register of standing test-audit rulings.

`register/<module>.tsv` holds one ruling for each test function of a module. `stamp`
records the fingerprint of each function once its ruling is final. `check` sorts every
function into unchanged, changed, new, source moved and gone, so that a later audit
judges only what is not unchanged. The format is in `rubric.md` (The register).

    python planning/test-audit/scripts/register.py stamp test_json
    python planning/test-audit/scripts/register.py check [--list] [test_json ...]
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
from collections import defaultdict
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
    "ruled_by": ("classifier", "verifier", "judge", "maintainer"),
    "confidence": ("high", "medium", "low", "-"),
}
GROUPS = ("unchanged", "changed", "new", "source moved", "gone")
Def = ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
NAME = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*")


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
    text = path.read_text()
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


def cmd_stamp(module: str) -> None:
    path, register = module_path(module), REGISTER / f"{module}.tsv"
    rows, sources = read_register(register), test_sources(path)
    no_row = sorted(set(sources) - set(rows))
    gone = sorted(
        n for n, r in rows.items() if r.ruling != "removed" and n not in sources
    )
    if no_row or gone:
        fail(
            f"{register}\nfunctions with no row: {no_row}\nrows with no function: {gone}"
        )
    ids, head = collect_ids(path), git("rev-parse", "--short=12", "HEAD").stdout.strip()
    stamped = current = 0
    for name, row in rows.items():
        if row.ruling == "removed":
            stamped += not row.audit_commit
            row.audit_commit = row.audit_commit or head
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


def definitions(files: dict[str, str]) -> Digests:
    """Map (path, qualified name) to a source hash for every def and class."""
    found: Digests = {}

    def walk(node: ast.AST, prefix: str, path: str, lines: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            qual = prefix
            if isinstance(child, Def):
                qual = f"{prefix}{child.name}"
                text = span_text(lines, child).encode()
                found[path, qual] = hashlib.sha256(text).hexdigest()
            walk(child, f"{qual}." if qual else "", path, lines)

    for path, text in files.items():
        if path.endswith(".py") and not path.startswith(f"{SOURCE}/tests/"):
            walk(ast.parse(text), "", path, text.splitlines())
    return found


def tree_definitions() -> Digests:
    paths = (ROOT / SOURCE).rglob("*.py")
    return definitions({p.relative_to(ROOT).as_posix(): p.read_text() for p in paths})


def commit_definitions(commit: str) -> Digests | None:
    """Return the definitions at a commit, or None when git cannot resolve it."""
    listing = git("ls-tree", "-r", "--name-only", commit, SOURCE)
    if listing.returncode != 0:
        return None
    names = listing.stdout.splitlines()
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


class Audit:
    """Classify test functions against a register, reading each commit once."""

    def __init__(self) -> None:
        self.now = tree_definitions()
        self.before: dict[str, Digests | None] = {}

    def moved(self, row: Row, old: Digests) -> str:
        """Name the definitions in the reason that differ from the audit commit."""
        tokens = named_tokens(row.reason)
        was, now = named(old, tokens), named(self.now, tokens)
        if set(was.values()) == set(now.values()):
            return ""
        return ", ".join(
            sorted({k[1] for k in was.keys() | now.keys() if was.get(k) != now.get(k)})
        )

    def classify(self, row: Row | None, source: str, ids: Sequence[str]) -> Found:
        if row is None:
            return Found("", "new")
        if row.ruling == "removed":
            return Found("", "changed", "ruled removed but the function exists")
        if row.fingerprint != fingerprint(source, ids):
            return Found("", "changed")
        if row.audit_commit not in self.before:
            self.before[row.audit_commit] = commit_definitions(row.audit_commit)
        old = self.before[row.audit_commit]
        if old is None:
            return Found("", "changed", "unknown audit commit")
        names = self.moved(row, old)
        return Found("", "source moved", names) if names else Found("", "unchanged")


def check_module(audit: Audit, module: str) -> list[Found]:
    """Return one finding for each test function and each row without a function."""
    sources, register = test_sources(module_path(module)), REGISTER / f"{module}.tsv"
    if not register.is_file():
        return [Found(name, "not audited") for name in sources]
    ids, rows = collect_ids(module_path(module)), read_register(register)
    found = []
    for name, source in sources.items():
        found.append(
            audit.classify(rows.get(name), source, ids.get(name, []))._replace(
                function=name
            )
        )
    for name, row in rows.items():
        if name not in sources:
            found.append(Found(name, "removed" if row.ruling == "removed" else "gone"))
    return found


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


def print_group(group: str, audited: dict[str, list[Found]]) -> None:
    hits = [(m, f) for m, found in audited.items() for f in found if f.group == group]
    if hits:
        print(f"\n{group} ({len(hits)})")
    for module, f in hits:
        print(f"  {module}::{f.function}" + (f"  {f.note}" if f.note else ""))


def cmd_check(modules: list[str], list_only: bool) -> None:
    names = modules or [p.stem for p in sorted(TESTS.glob("test_*.py"))]
    audit = Audit()
    results = {m: check_module(audit, m) for m in names}
    if not list_only:
        return print_report(results)
    for module, found in results.items():
        for f in found:
            print(f"{module}::{f.function}\t{f.group}")


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    stamp = commands.add_parser("stamp", help="fingerprint a module's register rows")
    stamp.add_argument("module")
    check = commands.add_parser("check", help="sort the tests by audit state")
    check.add_argument("modules", nargs="*")
    check.add_argument(
        "--list", action="store_true", help="print only function and group"
    )
    args = parser.parse_args(argv)
    if args.command == "stamp":
        cmd_stamp(args.module.removesuffix(".py"))
    else:
        cmd_check([m.removesuffix(".py") for m in args.modules], args.list)


if __name__ == "__main__":
    main()
