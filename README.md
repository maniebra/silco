# SILCO (**S**ystem **I**llustration & **L**ayout **Co**mposer)

Silco is a tiny Python-first system design diagram generator. Build a diagram as code,
render it as inline SVG, export Mermaid text, or display it directly in IPython/Jupyter.

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
mermaid = d.to_mermaid()
```

In IPython/Jupyter:

```python
%load_ext silco.plugins.ipython
d
```

Plugins are categorized as `shapes`, `renderers`, `layouts`, and `presenters`.
Silco can auto-discover local plugin modules and installed package entry points:

```python
from silco import kernel

kernel.discover()
kernel.names("renderers")
kernel.names("presenters")
```
