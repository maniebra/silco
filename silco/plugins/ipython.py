from __future__ import annotations

from typing import Any

from silco.core import Diagram
from silco.core.kernel import SilcoKernel, kernel

PLUGIN_CATEGORY = "presenters"
PLUGIN_NAME = "ipython"
PLUGIN_DESCRIPTION = "Rich SVG/HTML representation for IPython and Jupyter notebooks."
PLUGIN_TAGS = ("notebook", "representation")


def as_svg(diagram: Diagram) -> str:
    return diagram.to_svg()


def as_html(diagram: Diagram) -> str:
    return diagram.to_html()


def install(ipython: Any | None = None) -> None:
    """Register rich display formatters for IPython/Jupyter."""

    if ipython is None:
        try:
            from IPython import get_ipython
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise RuntimeError("IPython is required to install the Silco display plugin") from exc
        ipython = get_ipython()
    if ipython is None:
        raise RuntimeError("No active IPython shell found")

    ipython.display_formatter.formatters["image/svg+xml"].for_type(Diagram, as_svg)
    ipython.display_formatter.formatters["text/html"].for_type(Diagram, as_html)


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        install,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


def load_ipython_extension(ipython: Any) -> None:
    install(ipython)


def unload_ipython_extension(ipython: Any) -> None:
    for mime in ("image/svg+xml", "text/html"):
        formatter = ipython.display_formatter.formatters[mime]
        formatter.type_printers.pop(Diagram, None)


register_plugins(kernel)
