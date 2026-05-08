# SILCO (**S**ystem **I**llustration & **L**ayout **Co**mposer)

Silco is a tiny Python-first system design diagram generator. Build a diagram as code,
render it as inline SVG with the built-in core graphics backend, or display it directly in IPython/Jupyter.

```python
from silco import diagram

d = (
    diagram("Checkout")
    .node("user", "User", kind="actor")
    .node("api", "API", kind="service", group="app")
    .node("db", "Orders DB", kind="database", group="data")
    .connect("user", "api", "HTTPS")
    .connect("api", "db", "SQL")
)

svg = d.to_svg()
```

Choose an SVG style and pass layout/rendering options directly:

```python
# Built-in style options: "modern" and "uml"
svg = d.to_svg(style="uml", direction="LR", title=True)
```

If you want consistent rendering even before style plugins are discovered, the
default `"modern"` style is available as a fallback.

In IPython/Jupyter:

```python
%load_ext silco.plugins.ipython
d
```

Export as PDF with the optional CairoSVG-backed plugin:

```bash
pip install "silco[pdf]"
```

```python
d.save_pdf("checkout.pdf")
pdf_bytes = d.to_pdf()
```

Plugins are categorized as `shapes`, `renderers`, `layouts`, and `presenters`.
Silco can auto-discover local plugin modules and installed package entry points:

```python
from silco import kernel

kernel.discover()
kernel.names("renderers")
kernel.names("presenters")
```
