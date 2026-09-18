"""Tests for the comparison logic in ``ab.py``.

The worktree and subprocess orchestration is proven by running the script;
see ``README.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .ab import (
    check_measured_tree,
    check_same_interpreter,
    compare,
    fastest,
    judge,
    load_minimums,
    main,
    typical,
)


def write_run(
    path: Path,
    minimums: dict[str, float],
    prov_path: str = "",
    python: tuple[str, str] = ("CPython", "3.12.11"),
) -> Path:
    data = {
        "prov_path": prov_path,
        "machine_info": {
            "python_implementation": python[0],
            "python_version": python[1],
        },
        "benchmarks": [
            {"fullname": name, "stats": {"min": value, "mean": value * 3}}
            for name, value in minimums.items()
        ],
    }
    path.write_text(json.dumps(data))
    return path


def test_load_minimums_reads_min_not_mean(tmp_path):
    run = write_run(tmp_path / "run.json", {"bench::a": 0.5})
    assert load_minimums(run) == {"bench::a": 0.5}


def test_fastest_keeps_the_lowest_reading_per_benchmark():
    passes = [{"a": 1.0, "b": 2.0}, {"a": 0.8, "b": 2.5}]
    assert fastest(passes) == {"a": 0.8, "b": 2.0}


def test_fastest_keeps_a_benchmark_seen_in_one_pass_only():
    assert fastest([{"a": 1.0}, {"a": 1.1, "b": 3.0}]) == {"a": 1.0, "b": 3.0}


def test_typical_is_the_median_of_the_per_pass_minimums():
    passes = [{"a": 0.092}, {"a": 0.122}, {"a": 0.120}]
    assert typical(passes) == {"a": 0.120}


def test_typical_skips_a_pass_that_lacks_the_benchmark():
    assert typical([{"a": 1.0}, {"a": 3.0, "b": 2.0}]) == {"a": 2.0, "b": 2.0}


def never_called():
    raise AssertionError("no confirmation pass is due")


def test_judge_accepts_a_green_result_without_another_pass():
    readings = {"base": [{"a": 1.0}, {"a": 1.01}], "head": [{"a": 1.05}, {"a": 1.0}]}
    rows, statistic = judge(readings, 0.10, never_called)
    assert statistic == "min"
    assert not any(row.regressed for row in rows)


def test_judge_outvotes_one_fast_base_pass():
    # test_equality on the push run of 6bc9db1, which changed no code: one base
    # pass ran 25% faster than the rest and the fastest round reported +25.1%.
    readings = {
        "base": [{"eq": 0.1219}, {"eq": 0.0921}],
        "head": [{"eq": 0.1223}, {"eq": 0.1152}],
    }

    def another_pass():
        readings["base"].append({"eq": 0.1201})
        readings["head"].append({"eq": 0.1188})

    rows, statistic = judge(readings, 0.10, another_pass)
    assert statistic == "median"
    assert [(row.base, row.head, row.regressed) for row in rows] == [
        (0.1201, 0.1188, False)
    ]


def test_judge_keeps_a_regression_that_survives_the_confirmation_pass():
    readings = {"base": [{"a": 1.0}, {"a": 1.02}], "head": [{"a": 1.3}, {"a": 1.31}]}

    def another_pass():
        readings["base"].append({"a": 1.01})
        readings["head"].append({"a": 1.29})

    rows, statistic = judge(readings, 0.10, another_pass)
    assert statistic == "median"
    assert [row.regressed for row in rows] == [True]


def test_compare_flags_only_changes_above_the_threshold():
    base = {"slow": 1.0, "edge": 1.0, "fast": 1.0}
    head = {"slow": 1.5, "edge": 1.25, "fast": 0.5}
    rows = compare(base, head, threshold=0.25)
    assert {r.name: r.regressed for r in rows} == {
        "slow": True,
        "edge": False,
        "fast": False,
    }
    assert next(r for r in rows if r.name == "slow").change == 0.5


def test_compare_reports_a_one_sided_benchmark_without_failing():
    rows = compare({"old": 1.0}, {"new": 1.0}, threshold=0.10)
    assert [(r.name, r.base, r.head, r.regressed) for r in rows] == [
        ("new", None, 1.0, False),
        ("old", 1.0, None, False),
    ]


def test_check_measured_tree_accepts_a_path_inside_the_tree(tmp_path):
    tree = tmp_path / "base"
    run = write_run(tmp_path / "r.json", {}, str(tree / "src/prov/__init__.py"))
    check_measured_tree(run, tree)


def test_check_measured_tree_rejects_the_other_tree(tmp_path):
    run = write_run(
        tmp_path / "r.json", {}, str(tmp_path / "head/src/prov/__init__.py")
    )
    with pytest.raises(SystemExit, match="measured"):
        check_measured_tree(run, tmp_path / "base")


def test_check_same_interpreter_accepts_matching_runs(tmp_path):
    base = write_run(tmp_path / "base.json", {})
    head = write_run(tmp_path / "head.json", {})
    check_same_interpreter(base, head)


def test_check_same_interpreter_rejects_a_different_interpreter(tmp_path):
    base = write_run(tmp_path / "base.json", {})
    head = write_run(tmp_path / "head.json", {}, python=("PyPy", "3.11.15"))
    with pytest.raises(
        SystemExit, match=r"CPython 3\.12\.11.*PyPy 3\.11\.15.*--python"
    ):
        check_same_interpreter(base, head)


def test_main_compares_saved_runs(tmp_path, capsys):
    base = write_run(tmp_path / "base.json", {"bench::a": 1.0, "bench::b": 1.0})
    head = write_run(tmp_path / "head.json", {"bench::a": 1.05, "bench::b": 1.3})
    assert main(["--from-json", str(base), str(head)]) == 1
    out = capsys.readouterr().out
    assert "+30.0%  REGRESSION" in out
    assert "+5.0%" in out

    assert main(["--from-json", str(base), str(head), "--threshold", "0.5"]) == 0
