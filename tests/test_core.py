import unittest
from types import SimpleNamespace

from silco import Diagram, Flow, diagram


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

        self.assertIn('class="cluster"', svg)
        self.assertIn(">app</text>", svg)
        self.assertIn(">RESP</text>", svg)

    def test_unknown_edge_endpoint_fails(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "unknown target node"):
            d.connect("api", "missing")

    def test_unknown_flow_endpoint_fails(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "unknown target node"):
            d.flow("api", "missing")

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
        self.assertIn("#1168bd", default_svg)
        self.assertIn("#dbeafe", uml_svg)

    def test_database_nodes_use_database_glyph_in_modern_style(self) -> None:
        svg = diagram("Inventory").node("db", "Orders DB", kind="database").to_svg(style="modern")

        self.assertIn("Orders DB", svg)
        self.assertIn("Database", svg)
        self.assertIn("#438dd5", svg)

    def test_svg_renderer_keeps_rtl_text_inside_graphviz_bounds(self) -> None:
        svg = (
            diagram("سکوی تجارت الکترونیک", direction="RL")
            .node("orders", "سرویس سفارش", kind="service")
            .node("db", "پایگاه داده سفارش", kind="database")
            .connect("orders", "db", "ماندگاری سفارش", protocol="SQL")
            .to_svg()
        )

        self.assertRegex(
            svg,
            r'<text[^>]*text-anchor="end"[^>]*direction="rtl"[^>]*>سرویس سفارش</text>',
        )
        self.assertRegex(
            svg,
            r'<text[^>]*text-anchor="middle"[^>]*direction="rtl"[^>]*>سکوی تجارت الکترونیک</text>',
        )
        self.assertRegex(
            svg,
            r'<text[^>]*text-anchor="end"[^>]*direction="rtl"[^>]*>ماندگاری سفارش \(SQL\)</text>',
        )

    def test_modern_style_is_a_diagrams_preset(self) -> None:
        from silco.core.renderers.diagrams_backend import DiagramStyle
        from silco.plugins.renderers.styles import modern

        self.assertIsInstance(modern.STYLE, DiagramStyle)
        self.assertEqual("modern", modern.STYLE.name)
        self.assertIn("database", modern.STYLE.node_kind_attr)

    def test_unknown_style_fails_fast(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "Unknown SVG style"):
            d.to_svg(style="does-not-exist")

    def test_grid_layout_has_looser_vertical_spacing(self) -> None:
        d = (
            diagram("Grid")
            .node("a", "A")
            .node("b", "B")
            .node("c", "C")
            .node("d", "D")
        )

        layout = d.layout("grid", node_gap=48, node_height=72)
        rows = sorted({node.y for node in layout.nodes.values()})
        self.assertGreaterEqual(len(rows), 2)
        self.assertEqual(rows[1] - rows[0], 72 + 48 * 1.5)

    def test_flow_relations_render_in_svg_and_mermaid(self) -> None:
        d = (
            diagram("Flow")
            .node("api", "API", group="app")
            .node("queue", "Queue", kind="queue", group="app")
            .flow("api", "queue", protocol="AMQP")
        )

        svg = d.to_svg()
        mermaid = d.to_mermaid()

        self.assertIn(">AMQP</text>", svg)
        self.assertIn("api -->|AMQP| queue", mermaid)

    def test_flow_model_is_exported(self) -> None:
        f = Flow(source="a", target="b", label="sync")
        self.assertEqual(f.display_label, "sync")

    def test_layout_separates_overlapping_groups(self) -> None:
        d = (
            diagram("Groups", direction="LR")
            .node("a", "A", group="g1", line=0)
            .node("b", "B", group="g1", line=1)
            .node("c", "C", group="g2", line=0)
            .node("d", "D", group="g2", line=1)
            .connect("a", "b")
            .connect("c", "d")
        )
        layout = d.layout("dag", width=700, node_width=180, node_height=84, node_gap=40)

        def box(group_id: str) -> tuple[float, float, float, float]:
            members = [layout.nodes[node.id] for node in d.nodes.values() if node.group == group_id]
            left = min(item.x for item in members)
            top = min(item.y for item in members)
            right = max(item.x + item.width for item in members)
            bottom = max(item.y + item.height for item in members)
            return left, top, right, bottom

        g1 = box("g1")
        g2 = box("g2")
        overlap = not (
            g1[2] <= g2[0]
            or g2[2] <= g1[0]
            or g1[3] <= g2[1]
            or g2[3] <= g1[1]
        )
        self.assertFalse(overlap)

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
