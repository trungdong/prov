# Security Policy

## Supported versions

| Version | Supported          | Fixes               |
| ------- | ------------------ | ------------------- |
| 3.x     | :white_check_mark: | All fixes           |
| 2.x     | :white_check_mark: | Security fixes only |
| < 2.0   | :x:                | None                |

The latest 3.x release receives all fixes. The most recent 2.x release receives security
fixes only. The back-port programme that followed the 3.0.0 release closed with 2.5.3, so
bug fixes are no longer back-ported to 2.x. New features and behaviour-breaking corrections
were never back-ported and stay on 3.x. Releases before 2.0 are no longer supported.

Both supported lines require Python 3.10 or later. 3.x has required it from the outset
and 2.x from 2.3.0 onwards. Earlier 2.x releases support Python 3.9 and later. The
`classifiers` in a release's `pyproject.toml` or `setup.py` list its exact supported
Python versions.

## Reporting a vulnerability

Report security vulnerabilities privately through
[GitHub's private vulnerability reporting](https://github.com/trungdong/prov/security/advisories/new)
for this repository, not as a public issue.

Include as much detail as you can. The affected versions, the vulnerable code path, and
steps to reproduce or a proof of concept all help.

We aim to acknowledge new reports within 5 business days and to give an initial assessment
(validity, severity and expected timeline for a fix) within 14 days. Confirmed
vulnerabilities are fixed in a patch release and disclosed through a GitHub security
advisory once a fix is available.
