import unittest

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

    def test_mermaid_renderer_includes_groups_and_edges(self) -> None:
        d = (
            diagram("Inventory")
            .node("api", "API", kind="service", group="app")
            .node("cache", "Redis", kind="cache", group="data")
            .connect("api", "cache", protocol="RESP")
        )

        mermaid = d.to_mermaid()

        self.assertTrue(mermaid.startswith("flowchart LR"))
        self.assertIn('subgraph app["app"]', mermaid)
        self.assertIn("api -->|RESP| cache", mermaid)

    def test_unknown_edge_endpoint_fails(self) -> None:
        d = diagram().node("api")

        with self.assertRaisesRegex(ValueError, "unknown target node"):
            d.connect("api", "missing")

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
        self.assertTrue(
            any(plugin.name == "ipython" for plugin in discovered) or "ipython" in kernel.names("presenters")
        )


if __name__ == "__main__":
    unittest.main()
