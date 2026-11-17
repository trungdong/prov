"""Write coverage-nominations.tsv and item-arcsets.tsv from a per-test coverage run.

Input is the SQLite file of a run made with `--cov-branch --cov-context=test`, and the
list of collected item ids (`pytest --collect-only -q`, one id per line), which adds
the items that touch no measured source. An arc is a branch pair in a file under
`src/prov/`, outside `src/prov/tests/`. A function's arcs are the union over its items.

`coverage-nominations.tsv`, one row per test function:

    module, function    the test
    n_items             collected items of the function
    n_arcs              arcs its items run
    n_unique_arcs       arcs that no other function runs
    n_distinct_item_arcsets  different arc sets among its items
    identical_to        up to 5 functions with the same arc set
    smallest_supersets  up to 3 functions with a larger arc set that contains it
                        (the Hypothesis module is skipped), as `module::function(size)`
    top_source_files    the three source files with most of its arcs, as `file:count`

`item-arcsets.tsv`, one row per parametrised function: its item count, the number of
distinct arc sets and the largest groups of items that share one (`count:ids`).

    python planning/test-audit/scripts/coverage_nominations.py \\
        <coverage.sqlite> <collected-items.txt> <out-dir> [--repo <repo-root>]
"""

from __future__ import annotations

import argparse
import ast
import collections
import sqlite3
from collections.abc import Sequence
from pathlib import Path

Key = tuple[str, str]
Arcs = frozenset[int]


def test_functions(repo: Path) -> list[Key]:
    out: set[Key] = set()
    for path in sorted((repo / "src/prov/tests").glob("test_*.py")):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and (
                node.name.startswith("test_")
            ):
                out.add((path.name, node.name))
    return sorted(out)


def parse_context(ctx: str) -> tuple[str, str, str] | None:
    """Return (module, function, item_id) or None for a non-test context."""
    if "::" not in ctx or "|" not in ctx:
        return None
    body, phase = ctx.rsplit("|", 1)
    if phase not in ("setup", "run", "teardown"):
        return None
    path, test_id = body.split("::", 1)
    return Path(path).name, test_id.split("[", 1)[0], body


def load_arcs(
    db: Path, collected: Path
) -> tuple[dict[str, set[int]], dict[str, Key], dict[int, str]]:
    """Return arcs by item, the function of each item and the measured source files."""
    con = sqlite3.connect(db)
    files = {
        i: p
        for i, p in con.execute("select id, path from file")
        if "/src/prov/" in p and "/src/prov/tests/" not in p
    }
    ctxs = {}
    for i, c in con.execute("select id, context from context"):
        if parsed := parse_context(c):
            ctxs[i] = parsed
    item_arcs: dict[str, set[int]] = collections.defaultdict(set)
    item_func: dict[str, Key] = {}
    for fid, cid, a, b in con.execute(
        "select file_id, context_id, fromno, tono from arc"
    ):
        if fid in files and cid in ctxs:
            mod, fn, body = ctxs[cid]
            item_arcs[body].add((fid << 42) | ((a + 1048576) << 21) | (b + 1048576))
            item_func[body] = (mod, fn)
    for mod, fn, body in ctxs.values():
        item_func.setdefault(body, (mod, fn))
        item_arcs.setdefault(body, set())
    for line in collected.read_text().splitlines():
        if parsed := parse_context(line + "|run"):
            item_func.setdefault(parsed[2], (parsed[0], parsed[1]))
            item_arcs.setdefault(parsed[2], set())
    return item_arcs, item_func, files


def label(k: Key) -> str:
    return f"{k[0]}::{k[1]}"


def supersets(k: Key, func_arcs: dict[Key, Arcs], by_size: list[Key]) -> list[str]:
    s, found = func_arcs[k], []
    for o in by_size:
        if len(func_arcs[o]) <= len(s) or o[0] == "test_property_roundtrip.py":
            continue
        if s < func_arcs[o]:
            found.append(f"{label(o)}({len(func_arcs[o])})")
            if len(found) == 3:
                break
    return found


def top_files(arcs: Arcs, files: dict[int, str]) -> str:
    per_file = collections.Counter(Path(files[a >> 42]).name for a in arcs)
    return ",".join(f"{n}:{c}" for n, c in per_file.most_common(3))


def nomination_rows(
    funcs: list[Key],
    func_items: dict[Key, list[str]],
    item_arcs: dict[str, set[int]],
    files: dict[int, str],
) -> list[list[str]]:
    func_arcs: dict[Key, Arcs] = {}
    for k in funcs:
        union: set[int] = set()
        for body in func_items.get(k, []):
            union |= item_arcs[body]
        func_arcs[k] = frozenset(union)
    cover: collections.Counter[int] = collections.Counter()
    for s in func_arcs.values():
        cover.update(s)
    by_size = sorted(funcs, key=lambda k: len(func_arcs[k]))
    by_set: dict[Arcs, list[Key]] = collections.defaultdict(list)
    for k in funcs:
        by_set[func_arcs[k]].append(k)
    rows = []
    for k in funcs:
        s, items = func_arcs[k], func_items.get(k, [])
        distinct = len({frozenset(item_arcs[b]) for b in items}) if items else 0
        ident = [label(o) for o in by_set[s] if o != k][:5]
        sup = supersets(k, func_arcs, by_size) if s else []
        top = top_files(s, files)
        unique = sum(1 for a in s if cover[a] == 1)
        counts = [len(items), len(s), unique, distinct]
        rows.append([*k, *map(str, counts), ",".join(ident), ",".join(sup), top])
    return rows


def arcset_rows(
    funcs: list[Key], func_items: dict[Key, list[str]], item_arcs: dict[str, set[int]]
) -> list[str]:
    lines = []
    for k in funcs:
        items = func_items.get(k, [])
        if len(items) <= 1:
            continue
        groups: dict[Arcs, list[str]] = collections.defaultdict(list)
        for b in items:
            groups[frozenset(item_arcs[b])].append(b.split("::", 1)[1][len(k[1]) :])
        ordered = sorted(groups.values(), key=lambda g: -len(g))
        text = "; ".join(f"{len(g)}:{','.join(g[:3])}" for g in ordered[:8])
        lines.append(f"{k[0]}\t{k[1]}\t{len(items)}\t{len(groups)}\t{text}\n")
    return lines


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("coverage_db", type=Path, help="SQLite file from coverage")
    parser.add_argument("collected_items", type=Path, help="pytest --collect-only -q")
    parser.add_argument(
        "out_dir", type=Path, help="folder that receives the .tsv files"
    )
    default_repo = Path(__file__).resolve().parents[3]
    parser.add_argument("--repo", type=Path, default=default_repo)
    args = parser.parse_args(argv)
    funcs = test_functions(args.repo)
    item_arcs, item_func, files = load_arcs(args.coverage_db, args.collected_items)
    func_items: dict[Key, list[str]] = collections.defaultdict(list)
    for body, key in item_func.items():
        func_items[key].append(body)
    rows = nomination_rows(funcs, func_items, item_arcs, files)
    header = (
        "module function n_items n_arcs n_unique_arcs n_distinct_item_arcsets "
        "identical_to smallest_supersets top_source_files"
    )
    with (args.out_dir / "coverage-nominations.tsv").open("w") as f:
        f.write("\t".join(header.split()) + "\n")
        f.writelines("\t".join(r) + "\n" for r in rows)
    sets = arcset_rows(funcs, func_items, item_arcs)
    with (args.out_dir / "item-arcsets.tsv").open("w") as f:
        f.write("module\tfunction\tn_items\tn_distinct_item_arcsets\tgroups\n")
        f.writelines(sets)
    print(len(rows), "functions;", len(sets), "parametrised")


if __name__ == "__main__":
    main()
