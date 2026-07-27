# Security Policy

## Supported Versions

The latest `3.x` release is actively maintained and receives all fixes.
The most recent `2.x` release receives security fixes only — no bug fixes,
no new features. `1.x` and earlier are no longer supported.

| Version | Supported          | Fixes               |
| ------- | ------------------ | ------------------- |
| 3.x     | :white_check_mark: | All fixes           |
| 2.x     | :white_check_mark: | Security fixes only |
| < 2.0   | :x:                | None                |

Both supported lines require Python 3.10 or later: `3.x` from the outset,
and `2.x` from `2.3.0` onwards. Earlier `2.x` releases support Python 3.9+;
consult the `classifiers` in a given release's `pyproject.toml`/`setup.py`
for its exact supported Python versions.

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
