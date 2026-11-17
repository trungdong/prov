"""Write provenance.tsv: the git history of each test function.

For each module-level `test_*` function in `src/prov/tests/test_*.py`, the file holds
one tab-separated row with these columns:

    module        test file name
    function      test function name
    lineno        line of the `def`
    first_sha     abbreviated hash of the first commit that added `def <function>(`
    first_date    date of that commit
    first_subject subject line of that commit
    refs          issue references (`#123`) in the test's text, its comment block and
                  the messages of the commits that touched it
    n_commits     number of commits that touched the function

Run it from any directory. The output folder must exist.

    python planning/test-audit/scripts/provenance.py <out-dir> [--repo <repo-root>]
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

TESTS = "src/prov/tests"
REF = re.compile(r"(?<![\w&])#(\d+)\b")
COLUMNS = "module function lineno first_sha first_date first_subject refs n_commits"
Item = tuple[str, str, int, str]


def git(repo: Path, *args: str) -> tuple[int, str]:
    r = subprocess.run(
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
            items.append((path.name, node.name, node.lineno, "\n".join(body)))
    return items


def refs_in(text: str) -> set[int]:
    return {int(m) for m in REF.findall(text)}


def work(repo: Path, item: Item) -> list[str]:
    module, func, lineno, text = item
    rel = f"{TESTS}/{module}"
    _, out = git(
        repo,
        *("log", "--reverse", "--format=%h%x09%ad%x09%s", "--date=short"),
        *(f"-Sdef {func}(", "--", f"{TESTS}/"),
    )
    first = out.splitlines()[0].split("\t", 2) if out.strip() else ["", "", ""]
    sha_s = [line.split("\t")[0] for line in out.splitlines()]
    rc, out = git(
        repo, "log", f"-L:{func}:{rel}", "--format=COMMIT %h%n%B%nENDCOMMIT", "-s"
    )
    refs = refs_in(text)
    if rc == 0 and out.strip():
        refs |= refs_in(out)
        n = len(re.findall(r"^COMMIT (\w+)$", out, re.M))
    else:
        n = len(sha_s)
        for sha in sha_s:
            refs |= refs_in(git(repo, "show", "-s", "--format=%B", sha)[1])
    refs_s = ",".join(f"#{r}" for r in sorted(refs))
    return [module, func, str(lineno), first[0], first[1], first[2], refs_s, str(n)]


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "out_dir", type=Path, help="folder that receives provenance.tsv"
    )
    default_repo = Path(__file__).resolve().parents[3]
    parser.add_argument("--repo", type=Path, default=default_repo)
    args = parser.parse_args(argv)
    items = collect(args.repo)
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(partial(work, args.repo), items))
    with (args.out_dir / "provenance.tsv").open("w") as f:
        f.write("\t".join(COLUMNS.split()) + "\n")
        for r in rows:
            f.write("\t".join(c.replace("\t", " ") for c in r) + "\n")
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
