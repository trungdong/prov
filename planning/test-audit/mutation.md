# Mutation check

The mutation check shows whether removing or merging tests leaves a detected mutant undetected. It was tested with mutmut 3.8.1. Start mutmut with `uv run --with mutmut`, so that no dependency changes. Run it in a scratch worktree of the branch under test. Never commit the configuration.

## Scope

The coordinator names the source files to mutate, from these rules. For a removal, take every file where the candidates cover a line that fewer than five other test functions cover, and the files the candidates' own calls pass through: the model path of the call under test, and the one serializer or reader the module is about. For a merge, take the files the merged tests exercise, by the same rule. A shared module that runs every serializer (`test_statements.py`, `test_attributes.py`, `test_qnames.py`, `test_examples.py`) does not add every serializer this way. Count the mutants of the scope before the baseline runs, as the section Count the mutants says.

## Configuration

Append this to the scratch worktree's `pyproject.toml`. Set `only_mutate` to the source files the check covers. It can name several. Keep every `--deselect` pair in every run, baseline included.

```toml
[tool.mutmut]
source_paths = ["src/prov/"]
only_mutate = ["src/prov/serializers/provjson.py"]
pytest_add_cli_args = [
    "-p", "no:cacheprovider",
    # This profile fixes the Hypothesis examples, so a mutant that only the property tests kill gets the same status in every run. It runs 50 examples, not the default 200.
    "--hypothesis-profile=ci",
    # These tests fail whatever is mutated.
    "--deselect", "src/prov/tests/test_provn_profiles.py::test_lenient_warning_reports_the_read_call_site",
    "--deselect", "src/prov/tests/test_read.py::test_read_auto_detect_emits_the_winners_warnings_once_at_the_caller",
    "--deselect", "src/prov/tests/test_read.py::test_read_auto_detect_emits_under_the_callers_module_name",
    # These tests fail when dot.py is mutated.
    "--deselect", "src/prov/tests/test_dot.py::test_unset_endpoint_inside_a_bundle_reports_the_prov_to_dot_call_site",
    "--deselect", "src/prov/tests/test_dot.py::test_prov_to_dot_warns_once_for_a_bundle_that_is_not_a_document",
    # These tests fail when bundle.py or records.py is mutated.
    "--deselect", "src/prov/tests/test_dot.py::test_plot_warns_once_and_saves_a_nested_bundle",
    "--deselect", "src/prov/tests/test_model.py::test_bundle_unified_is_deprecated",
    "--deselect", "src/prov/tests/test_model.py::test_the_document_argument_is_deprecated",
    "--deselect", "src/prov/tests/test_provn_profiles.py::test_lenient_warning_reports_the_deserialize_call_site",
    "--deselect", "src/prov/tests/test_xml.py::test_nested_reference_warning_is_attributed_to_the_caller",
]
pytest_add_cli_args_test_selection = ["src/prov/tests/"]
process_isolation = "forkserver"
```

Write the command prefix once as a script, `mm.sh`, so a shell guard does not refuse a long line:

```bash
uv run --python 3.12 --extra rdf --extra xml --extra dot --extra graph --with mutmut mutmut "$@"
```

## Count the mutants

Count before the baseline, never from the baseline's progress line.

1. Append the configuration and write `mm.sh`, as the section above says.
2. Delete `mutants/`. Delete `/tmp/mutation/` if it exists, and make it again, empty.
3. Run `mm.sh run no_such_mutant`. It builds the mutants and runs the suite once to map tests to mutants. Then it stops with `AssertionError: Filtered for specific mutants, but nothing matches`, before any mutant runs. Any other ending is a failing test, and Pitfalls says how to handle one.
4. Save the list once: `mm.sh results --all true | sed 's/^ *//' > /tmp/mutation/count.txt`. Count all the mutants with `wc -l < /tmp/mutation/count.txt`, and each file's with `grep -c '^prov\.model\._values\.' /tmp/mutation/count.txt`, with that file's module path in the pattern.
5. Record the counts and the commands. If the total comes to more than about 3,000, stop and report the files and counts for the coordinator to rule.

## Baseline

1. Delete `mutants/` in the scratch worktree. Delete `/tmp/mutation/` if it exists, and make it again, empty, for the result files. A file left in the worktree can reach a commit.
2. Run `mm.sh run --max-children 8`.
3. Save the result: `mm.sh results --all true | sed 's/^ *//' > /tmp/mutation/baseline.txt`. Each line reads `<id>: killed`, `survived`, `no tests` or `not checked`.
4. Note the wall time of this run and of every later run. The report gives each one, so that the cost of the check stays a measured figure.

## Compare a removal

1. Add a `--deselect`, `<item id>` pair to `pytest_add_cli_args` for each item of each test to remove. Put them at the end of the array under their own comment, `# Removal candidates for this run.`, so they stay apart from the permanent groups.
2. Run `mm.sh run --max-children 8 $(grep ': killed' /tmp/mutation/baseline.txt | sed 's/: killed//')`.
3. Save the result as `/tmp/mutation/removal.txt` in the same way.
4. List every id that `/tmp/mutation/removal.txt` shows as `survived` or `no tests`. These are the newly undetected mutants.

## Compare a merge

1. Apply the merge patch to the scratch worktree.
2. Delete `mutants/`.
3. Run `mm.sh run --max-children 8` from scratch.
4. Save the result as `/tmp/mutation/merge.txt`.
5. Run `diff /tmp/mutation/baseline.txt /tmp/mutation/merge.txt`. Any `killed` that becomes `survived` or `no tests` is a mutant that changed status.

## Pitfalls

- Keep `process_isolation = "forkserver"`. The default `fork` fails the clean run on a `test_identifier_slots.py` case.
- A rerun resets earlier results. Save `/tmp/mutation/baseline.txt` before the first rerun.
- Count `no tests` as undetected. It means every test mapped to the mutant is deselected.
- Check the collected count with `pytest --collect-only -q` before a run. A `--deselect` id that does not match exactly does nothing and raises no error.
- `--deselect` matches a prefix of the item id, and `-k` matches substrings. `--deselect src/prov/tests/test_read.py::test_read_auto_detects_xml` also removes `test_read_auto_detects_xml_from_seekable_stringio`. For a parametrised function, pass each item id with its `[...]` part. For a plain function whose name starts another's, use `-k "not <short> or <long>"`, for example `-k "not test_read_auto_detects_xml or test_read_auto_detects_xml_from_seekable_stringio"`. Check that the collected count fell by exactly the number of candidates.
- mutmut does not say which test killed a mutant. Only the run with and without the tests shows it.
- mutmut's trampoline adds a stack frame. The tests deselected in the configuration check the caller of a warning, so they fail under it and stay deselected in every run. The comment above each group in the configuration says when its tests fail. Deselecting them in every run costs nothing. Two other tests also check a warning's caller and may fail under the trampoline when the file that warns is mutated, `test_model.py::test_container_reads_are_deprecated` and `test_warnings.py::test_warn_outside_a_collection_warns_at_the_caller`. When a clean baseline fails on one of them, deselect it in that run and add it to the configuration above, in the group whose comment matches or under a new comment. A `--deselect` of a parametrised function's bare id removes all its items, so name the id with its `[...]` part only when one item is meant.
- Start mutmut in the foreground with the Bash tool's maximum timeout of 10 minutes. A run that takes longer moves to the background. Wait for its exit notice, run nothing else in that worktree until then, and never poll for it, for example with `pgrep -f "mutmut run"`, whose pattern matches the waiting shell's own command line, so the loop never ends. To check that no run is left, use `ps -ax -o pid,command | grep -E 'mutmut (run|results)' | grep -v grep`.
- Do not run the check beside the gate runner or the benchmark A/B. It starts 8 worker processes. Queue the gates between mutation runs.
