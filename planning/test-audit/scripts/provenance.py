"""Write provenance.tsv: the git history of each test function.

For each module-level `test_*` function in `src/prov/tests/test_*.py`, the file holds
one tab-separated row with these columns:

    module        test file name
    function      test function name
    lineno        line of the `def`
    first_sha     abbreviated hash of the oldest commit that added `def <function>(`
                  to a test module. For a name that several modules define, the
                  commit in the function's line history that added its `def` line
    first_date    date of that commit
    first_subject subject line of that commit
    text_refs     issue references (`#123`) in the test's own text and the comment
                  block above it
    history_refs  issue references in the messages of the commits in the function's
                  line history (`git log -L`, which follows the lines across renames
                  but not into another module), less those already in text_refs. A
                  commit message often names an issue that belongs to another change
                  in the same commit
    n_commits     number of commits in that line history

Run it from any directory. The output folder must exist.

    python planning/test-audit/scripts/provenance.py <out-dir> [--repo <repo-root>]
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess  # nosec B404
from collections import Counter
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

TESTS = "src/prov/tests"
REF = re.compile(r"(?<![\w&])#(\d+)\b")
COLUMNS = (
    "module function lineno first_sha first_date first_subject "
    "text_refs history_refs n_commits"
)
MARK = "@@\t"
Item = tuple[str, str, int, int, int, str]


def git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(  # nosec B603 B607 - nosemgrep
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        errors="replace",
    )
    return r.returncode, r.stdout


def comment_block(lines: list[str], start: int) -> list[str]:
    """Return the comment lines directly above the 1-based line `start`."""
    above: list[str] = []
    i = start - 2
    while i >= 0 and lines[i].lstrip().startswith("#"):
        above.append(lines[i])
        i -= 1
    return above


def collect(repo: Path) -> list[Item]:
    items: list[Item] = []
    for path in sorted((repo / TESTS).glob("test_*.py")):
        src = path.read_text()
        lines = src.splitlines()
        for node in ast.parse(src).body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if not node.name.startswith("test_"):
                continue
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            body = comment_block(lines, start) + lines[start - 1 : node.end_lineno]
            end = node.end_lineno or node.lineno
            items.append(
                (path.name, node.name, node.lineno, start, end, "\n".join(body))
            )
    return items


def refs_in(text: str) -> set[int]:
    return {int(m) for m in REF.findall(text)}


def history(repo: Path, item: Item) -> list[str]:
    """Return the commits that touched the function, newest first, each as its
    marker line, message and patch, back to the commit that added its `def` line."""
    module, func, _, start, end, _ = item
    rc, out = git(
        repo,
        *("log", f"-L{start},{end}:{TESTS}/{module}", "--date=short"),
        "--format=" + MARK + "%h%x09%ad%x09%s%n%b",
    )
    commits = out.split(MARK)[1:] if rc == 0 else []

    # The line range also follows lines that an older test held before this one
    # took its place. The function's history starts where its `def` line was added.

    added = re.compile(rf"^\+\s*(?:async\s+)?def {func}\(", re.M)
    origin = max((i for i, c in enumerate(commits) if added.search(c)), default=-1)
    return commits[: origin + 1] if origin >= 0 else commits


def first_added(repo: Path, func: str) -> list[str]:
    """Return the hash, date and subject of the oldest commit that added
    `def <func>(` under either test folder, the current one or the one before 2017."""
    _, out = git(
        repo,
        *("log", "--reverse", "--format=%h%x09%ad%x09%s", "--date=short"),
        *(f"-Sdef {func}(", "--", f"{TESTS}/", "prov/tests/"),
    )
    return out.splitlines()[0].split("\t", 2) if out.strip() else ["", "", ""]


def work(repo: Path, shared: set[str], item: Item) -> list[str]:
    module, func, lineno, _, _, text = item
    commits = history(repo, item)

    # A test body can move between modules, which a line history does not follow, so
    # the first commit comes from the name. A name that several modules define is
    # ambiguous, and its first commit comes from the line history instead.

    first = ["", "", ""] if func in shared else first_added(repo, func)
    if not first[0] and commits:
        first = commits[-1].split("\n", 1)[0].split("\t", 2)
    messages = "\n".join(c.split("\ndiff --git ", 1)[0] for c in commits)
    text_refs = refs_in(text)
    history_refs = refs_in(messages) - text_refs
    return [
        *(module, func, str(lineno), *first),
        *(fmt_refs(text_refs), fmt_refs(history_refs), str(len(commits))),
    ]


def fmt_refs(refs: set[int]) -> str:
    return ",".join(f"#{r}" for r in sorted(refs))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "out_dir", type=Path, help="folder that receives provenance.tsv"
    )
    default_repo = Path(__file__).resolve().parents[3]
    parser.add_argument("--repo", type=Path, default=default_repo)
    args = parser.parse_args(argv)
    items = collect(args.repo)
    names = Counter(item[1] for item in items)
    shared = {name for name, count in names.items() if count > 1}
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(partial(work, args.repo, shared), items))
    with (args.out_dir / "provenance.tsv").open("w") as f:
        f.write("\t".join(COLUMNS.split()) + "\n")
        for r in rows:
            f.write("\t".join(c.replace("\t", " ") for c in r) + "\n")
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
