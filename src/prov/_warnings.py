"""Shared ``warnings.warn()`` stacklevel helper.

Attributing a warning to its caller with a fixed ``stacklevel`` only works
when every call path between the ``warn()`` site and the external caller
has the same number of frames. Several call paths do not (a serializer
reached directly vs. via :func:`prov.read`, or a relation drawn at the
top of a document vs. inside a nested bundle), so the stacklevel has to be
found by walking the real call stack instead.
"""

import sys
from types import FrameType


def external_stacklevel(skip: int = 1) -> int:
    """Return the ``stacklevel`` of the nearest frame outside ``prov``.

    Walks the call stack outward starting at the frame ``skip`` levels
    above the caller of this function, stopping at the first frame whose
    module is not ``prov`` or a ``prov.`` submodule. A frame in
    ``prov.tests.`` counts as external, since the test suite calls into
    ``prov`` directly and still wants the warning attributed to its own
    filename.

    Args:
        skip: Number of frames between this function and the ``warn()``
            call site whose stacklevel is being computed (default ``1``,
            i.e. this function's direct caller is that site).

    Returns:
        The ``stacklevel`` value to pass to ``warnings.warn()``, or
        ``skip + 1`` if the walk exhausts without finding an external frame.
    """
    frame: FrameType | None = sys._getframe(skip)
    level = skip
    while frame is not None:
        module_name = frame.f_globals.get("__name__", "")
        is_internal = module_name == "prov" or module_name.startswith("prov.")
        is_tests = module_name.startswith("prov.tests.")
        if not is_internal or is_tests:
            return level
        frame = frame.f_back
        level += 1
    return skip + 1
