"""``ProvWarning``, its 3.3.0 subclass and the shared stacklevel helper.

All live here, not in :mod:`prov.model.records`, so that :mod:`prov.identifier`
can emit them without importing :mod:`prov.model` and creating a cycle;
:mod:`prov.model` re-exports both warning classes under their public names.

Attributing a warning to its caller with a fixed ``stacklevel`` only works
when every call path between the ``warn()`` site and the external caller
has the same number of frames. Several call paths do not (a serializer
reached directly vs. via :func:`prov.read`, or a relation drawn at the
top of a document vs. inside a nested bundle), so the stacklevel has to be
found by walking the real call stack instead.
"""

import sys
from types import FrameType


class ProvWarning(Warning):
    """Base class for PROV model warnings."""


class ProvFutureRejectionWarning(ProvWarning):
    """Input that ``prov`` 3.2.x reads but 3.3.0 rejects or reads differently.

    ``prov`` still reads the input as before. Turn this class into an error,
    for example with ``warnings.simplefilter("error", ProvFutureRejectionWarning)``,
    to find every such input without failing on any other :class:`ProvWarning`.
    """


def future_rejection_message(detail: str, outcome: str = "reject this") -> str:
    """Return ``detail`` followed by the clause every 3.3.0 warning ends with.

    Args:
        detail: What was found, starting with its position where the
            format has one.
        outcome: What 3.3.0 does instead, completing ``"prov 3.3.0 will"``.

    Returns:
        For example ``"<detail>. prov 3.3.0 will reject this"``.
    """
    return f"{detail}. prov 3.3.0 will {outcome}"


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
