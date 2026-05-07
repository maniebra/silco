from __future__ import annotations

from pathlib import Path

from silco import diagram


def build_demo_diagram():
    return (
        diagram("Checkout PDF Demo")
        .node("user", "Shopper", kind="actor")
        .node("web", "Web App", kind="service", group="frontend")
        .node("api", "Checkout API", kind="service", group="backend")
        .node("payments", "Payments", kind="external")
        .node("orders", "Orders DB", kind="database", group="data")
        .connect("user", "web", "HTTPS")
        .connect("web", "api", "POST /checkout")
        .connect("api", "payments", "Authorize")
        .connect("api", "orders", "Persist order")
    )


def main() -> None:
    output_path = Path("checkout-demo.pdf")
    demo = build_demo_diagram()

    try:
        demo.save_pdf(output_path)
    except RuntimeError as exc:
        raise SystemExit(
            f"{exc}\nInstall the PDF extras first, for example: pip install 'silco[pdf]'"
        ) from exc

    print(f"Wrote {output_path.resolve()}")


if __name__ == "__main__":
    main()
