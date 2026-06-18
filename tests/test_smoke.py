"""Smoke tests that lock in Silco's public API surface and rendering contracts.

These tests exercise the public entry points without requiring Graphviz or any
optional plugin (so they can run on a vanilla CI image).
"""

from __future__ import annotations

import pytest

from silco import Diagram, Edge, Node, diagram, kernel


def test_public_surface_is_importable():
    from silco import (  # noqa: F401
        Canvas,
        Diagram,
        Edge,
        Element,
        Flow,
        Group,
        Node,
        PluginInfo,
        RenderConfig,
        diagram,
        kernel,
    )


def test_kernel_registers_builtin_layouts():
    names = kernel.names("layouts")
    assert "dag" in names
    assert "grid" in names


def test_kernel_registers_builtin_renderers():
    names = kernel.names("renderers")
    assert "svg" in names
    assert "mermaid" in names


def test_kernel_categories_match_constant():
    from silco.core import PLUGIN_CATEGORIES

    assert kernel.categories() == PLUGIN_CATEGORIES


def test_kernel_normalizes_category_aliases():
    assert kernel.normalize_category("renderer") == "renderers"
    assert kernel.normalize_category("renderers") == "renderers"
    assert kernel.normalize_category("style") == "styles"


def test_kernel_unknown_category_raises():
    with pytest.raises(ValueError):
        kernel.normalize_category("widgets")


def test_diagram_factory_returns_diagram():
    d = diagram("Demo")
    assert isinstance(d, Diagram)
    assert d.title == "Demo"
    assert d.direction == "LR"


def test_diagram_builder_chain_records_nodes_and_edges():
    d = (
        diagram("Test")
        .node("user", "User", kind="actor")
        .node("api", "API", kind="service", group="app")
        .connect("user", "api", "HTTPS")
    )
    assert "user" in d.nodes
    assert "api" in d.nodes
    assert isinstance(d.nodes["user"], Node)
    assert d.nodes["user"].kind == "actor"
    assert "app" in d.groups
    assert len(d.edges) == 1
    edge = d.edges[0]
    assert isinstance(edge, Edge)
    assert (edge.source, edge.target, edge.label) == ("user", "api", "HTTPS")


def test_connect_to_unknown_node_raises():
    d = diagram("Test").node("a", "A")
    with pytest.raises(ValueError):
        d.connect("a", "missing")


def test_duplicate_node_id_raises():
    d = diagram("Test").node("a", "A")
    with pytest.raises(ValueError):
        d.node("a", "A again")


def test_mermaid_output_includes_all_nodes_and_edges():
    d = (
        diagram("Test")
        .node("a", "A")
        .node("b", "B", group="g")
        .connect("a", "b", "calls")
    )
    output = d.to_mermaid()
    assert output.startswith("flowchart LR")
    assert "subgraph g" in output
    assert "a -->|calls| b" in output


def test_diagram_repr_summarises_counts():
    d = diagram("X").node("a", "A").node("b", "B").connect("a", "b")
    assert "2 nodes" in repr(d)
    assert "1 relations" in repr(d)
