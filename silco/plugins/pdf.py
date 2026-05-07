from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import Any

from silco.core import Diagram
from silco.core.kernel import SilcoKernel, kernel

PLUGIN_CATEGORY = "renderers"
PLUGIN_NAME = "pdf"
PLUGIN_DESCRIPTION = "PDF export renderer backed by the optional CairoSVG package."
PLUGIN_TAGS = ("export", "pdf", "vector")


def pdf_renderer(diagram: Diagram, **options: Any) -> bytes:
    """Render a diagram to PDF bytes.

    This plugin keeps CairoSVG optional so Silco remains lightweight unless PDF
    export is requested.
    """

    try:
        import cairosvg
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("PDF rendering requires the optional dependency: pip install silco[pdf]") from exc

    svg_options = dict(options.pop("svg_options", {}))
    svg_options.update({k: v for k, v in options.items() if k != "write_to"})
    svg = diagram.to_svg(**svg_options)
    return cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=options.get("write_to"))


def save_pdf(diagram: Diagram, path: str | PathLike[str], **options: Any) -> Path:
    """Render a diagram and write it to a PDF file."""

    target = Path(path)
    pdf_renderer(diagram, write_to=str(target), **options)
    return target


def register_plugins(registry: SilcoKernel = kernel) -> None:
    registry.register(
        PLUGIN_CATEGORY,
        PLUGIN_NAME,
        pdf_renderer,
        description=PLUGIN_DESCRIPTION,
        module=__name__,
        tags=PLUGIN_TAGS,
        auto_discovered=True,
    )


register_plugins(kernel)
