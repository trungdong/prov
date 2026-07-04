# Security Policy

## Supported Versions

Only the latest `2.x` release is actively maintained. Security fixes are
backported to the most recent `2.x` release; `1.x` and earlier are no
longer supported.

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| 1.x     | :x:                |
| < 1.0   | :x:                |

Starting with `2.3.0`, `prov` requires Python 3.10 or later. Earlier `2.x`
releases support Python 3.9+; consult the `classifiers` in a given
release's `pyproject.toml`/`setup.py` for its exact supported Python
versions.

## Reporting a Vulnerability

Please report security vulnerabilities privately, using [GitHub's private
vulnerability reporting](https://github.com/trungdong/prov/security/advisories/new)
for this repository, rather than opening a public issue.

Include as much detail as you can: affected version(s), the vulnerable
code path, and steps to reproduce or a proof of concept.

We aim to acknowledge new reports within 5 business days and to provide
an initial assessment (validity, severity, and expected timeline for a
fix) within 14 days. Confirmed vulnerabilities will be fixed in a
patch release and disclosed via a GitHub security advisory once a fix
is available.
