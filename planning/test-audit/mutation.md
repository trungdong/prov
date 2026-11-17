# Mutation check

The mutation check shows whether removing or merging tests leaves a detected mutant undetected. It was tested with mutmut 3.8.1. Start mutmut with `uv run --with mutmut`, so that no dependency changes. Run it in a scratch worktree of the branch under test. Never commit the configuration.

## Configuration

Append this to the scratch worktree's `pyproject.toml`. Set `only_mutate` to the source module the tests cover. Keep the three `--deselect` pairs in every run, baseline included.

```toml
[tool.mutmut]
source_paths = ["src/prov/"]
only_mutate = ["src/prov/serializers/provjson.py"]
pytest_add_cli_args = [
    "-p", "no:cacheprovider",
    "--deselect", "src/prov/tests/test_provn_profiles.py::test_lenient_warning_reports_the_read_call_site",
    "--deselect", "src/prov/tests/test_read.py::test_read_auto_detect_emits_the_winners_warnings_once_at_the_caller",
    "--deselect", "src/prov/tests/test_read.py::test_read_auto_detect_emits_under_the_callers_module_name",
]
pytest_add_cli_args_test_selection = ["src/prov/tests/"]
process_isolation = "forkserver"
```

Write the command prefix once as a script, `mm.sh`, so a shell guard does not refuse a long line:

```bash
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph --with mutmut mutmut "$@"
```

## Baseline

1. Delete `mutants/` in the scratch worktree.
2. Run `mm.sh run --max-children 8`.
3. Save the result: `mm.sh results --all true | sed 's/^ *//' > baseline.txt`. Each line reads `<id>: killed`, `survived`, `no tests` or `not checked`.

## Compare a removal

1. Add a `--deselect`, `<item id>` pair to `pytest_add_cli_args` for each item of each test to remove.
2. Run `mm.sh run --max-children 8 $(grep ': killed' baseline.txt | sed 's/: killed//')`.
3. Save the result as `removal.txt` in the same way.
4. List every id that `removal.txt` shows as `survived` or `no tests`. These are the newly undetected mutants.

## Compare a merge

1. Apply the merge patch to the scratch worktree.
2. Delete `mutants/`.
3. Run `mm.sh run --max-children 8` from scratch.
4. Save the result as `merge.txt`.
5. Run `diff baseline.txt merge.txt`. Any `killed` that becomes `survived` or `no tests` is a mutant that changed status.

## Pitfalls

- Keep `process_isolation = "forkserver"`. The default `fork` fails the clean run on a `test_identifier_slots.py` case.
- A rerun resets earlier results. Save `baseline.txt` before the first rerun.
- Count `no tests` as undetected. It means every test mapped to the mutant is deselected.
- Check the collected count with `pytest --collect-only -q` before a run. A `--deselect` id that does not match exactly does nothing and raises no error.
- `--deselect` matches a prefix of the item id. `--deselect src/prov/tests/test_read.py::test_read_auto_detects_xml` also removes `test_read_auto_detects_xml_from_seekable_stringio`. When one test's name starts another's, select with `-k` and check that the collected count fell by exactly the number of candidates.
- mutmut does not say which test killed a mutant. Only the run with and without the tests shows it.
- mutmut's trampoline adds a stack frame. The three tests in the configuration check the caller of a warning, so they fail under it and stay deselected in every run.
- Do not run the check beside the gate loop or the benchmark A/B. It starts 8 worker processes.
