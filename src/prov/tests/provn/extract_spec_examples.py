"""Extract the PROV-N examples from the W3C PROV-N and PROV-DM
Recommendations into ``spec/prov-n/`` and ``spec/prov-dm/``.

Fragments (anything not already a ``document ... endDocument``) are wrapped
in a document that declares a default namespace and every prefix the
fragment uses, each under ``http://example.org/<prefix>/``. Run from this
directory:

    uv run python extract_spec_examples.py

The Recommendations are fetched from w3.org; the generated files are
committed so the tests need no network.
"""

from __future__ import annotations

import html
import re
import urllib.request
from pathlib import Path

SOURCES = {
    "prov-n": "https://www.w3.org/TR/2013/REC-prov-n-20130430/",
    "prov-dm": "https://www.w3.org/TR/2013/REC-prov-dm-20130430/",
}
_BLOCK = re.compile(r'<pre class="codeexample"[^>]*>(.*?)</pre>', re.S)
_TAG = re.compile(r"<[^>]+>")
_PREFIX = re.compile(r"(?<![\w<:/])([A-Za-z][\w.-]*):(?=[\w%\\])")
_STRIP_STRINGS = re.compile(r'"(?:\\.|[^"\\])*"|<[^>]*>|\'(?:\\.|[^\'\\])*\'')


def wrap(fragment: str) -> str:
    stripped = _STRIP_STRINGS.sub("", fragment)
    prefixes = sorted(
        {m.group(1) for m in _PREFIX.finditer(stripped)} - {"prov", "xsd"}
    )
    # A default namespace covers the many illustrative fragments that use a
    # bare, unprefixed identifier; PROV-N requires one to be declared before
    # such an identifier can resolve.
    declarations = "  default <http://example.org/>\n"
    declarations += "".join(
        f"  prefix {p} <http://example.org/{p}/>\n" for p in prefixes
    )
    body = "".join(f"  {line}\n" for line in fragment.splitlines())
    return f"document\n{declarations}{body}endDocument\n"


def main() -> None:
    here = Path(__file__).parent
    for name, url in SOURCES.items():
        target = here / "spec" / name
        target.mkdir(parents=True, exist_ok=True)
        # Fixed W3C TR URLs, fetched only when regenerating the vendored corpus.
        page = urllib.request.urlopen(url).read().decode("utf-8")  # nosec B310
        for index, raw in enumerate(_BLOCK.findall(page), start=1):
            text = html.unescape(_TAG.sub("", raw)).strip("\n")
            if "endDocument" not in text:
                text = wrap(text)
            elif not text.endswith("\n"):
                text += "\n"
            (target / f"{name}-example-{index:02d}.provn").write_text(
                text, encoding="utf-8"
            )
        print(name, index, "examples")


if __name__ == "__main__":
    main()
