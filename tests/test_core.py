import unittest
from types import SimpleNamespace

from silco import Diagram, diagram


class CoreTest(unittest.TestCase):
    def test_diagram_builds_and_renders_svg(self) -> None:
        d = (
            diagram("Checkout")
            .node("user", "User", kind="actor")
            .node("api", "API", kind="service", group="app")
            .node("db", "Orders DB", kind="database", group="data")
            .connect("user", "api", "HTTPS")
            .connect("api", "db", "SQL")
        )

        svg = d.to_svg()

        self.assertIsInstance(d, Diagram)
        self.assertIn("<svg", svg)
        self.assertIn("Checkout", svg)
        self.assertIn("Orders DB", svg)
        self.assertIn("HTTPS", svg)

    def test_svg_renderer_includes_groups_and_edges(self) -> None:
        d = (
            diagram("Inventory")
            .node("api", "API", kind="service", group="app")
            .node("cache", "Redis", kind="cache", group="data")
            .connect("api", "cache", protocol="RESP")
        )

        svg = d.to_svg()

        self.assertIn('class="silco-group"', svg)
        self.assertIn(">app<", svg)
        self.assertIn(">RESP<", svg)

    def test_unknown_edge_endpoint_fails(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "unknown target node"):
            d.connect("api", "missing")

    def test_svg_renderer_supports_styles(self) -> None:
        d = (
            diagram("Styled")
            .node("api", "API", kind="service", group="app")
            .node("db", "DB", kind="database", group="data")
            .connect("api", "db", protocol="JDBC")
        )

        default_svg = d.to_svg(style="modern")
        uml_svg = d.to_svg(style="uml")

        self.assertNotEqual(default_svg, uml_svg)
        self.assertIn("modern-arrow", default_svg)
        self.assertIn("uml-arrow", uml_svg)

    def test_unknown_style_fails_fast(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "Unknown SVG style"):
            d.to_svg(style="does-not-exist")

class PluginRegistryTest(unittest.TestCase):
    def test_plugins_are_categorized_with_metadata(self) -> None:
        from silco.core import kernel

        self.assertIn("renderers", kernel.categories())
        self.assertIn("svg", kernel.names("renderer"))
        info = kernel.info("renderer", "svg")
        self.assertEqual("renderers", info.category)
        self.assertIn("builtin", info.tags)

    def test_auto_discovers_local_plugins(self) -> None:
        from silco.core import kernel

        discovered = kernel.discover(namespace="silco.plugins")

        self.assertIn("ipython", kernel.names("presenters"))
        self.assertIn("pdf", kernel.names("renderers"))
        self.assertTrue(
            any(plugin.name == "ipython" for plugin in discovered) or "ipython" in kernel.names("presenters")
        )

    def test_pdf_plugin_renders_with_optional_backend(self) -> None:
        import sys

        from silco.plugins import pdf

        calls = {}

        def svg2pdf(*, bytestring: bytes, write_to: str | None = None) -> bytes:
            calls["svg"] = bytestring
            calls["write_to"] = write_to
            return b"%PDF-1.7\n"

        original = sys.modules.get("cairosvg")
        sys.modules["cairosvg"] = SimpleNamespace(svg2pdf=svg2pdf)
        try:
            result = pdf.pdf_renderer(diagram("PDF").node("api", "API"))
        finally:
            if original is None:
                sys.modules.pop("cairosvg", None)
            else:
                sys.modules["cairosvg"] = original

        self.assertEqual(b"%PDF-1.7\n", result)
        self.assertIn(b"<svg", calls["svg"])
        self.assertIsNone(calls["write_to"])


if __name__ == "__main__":
    unittest.main()
