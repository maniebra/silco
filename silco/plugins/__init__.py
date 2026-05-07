from silco.core.kernel import PluginInfo, kernel


def discover() -> tuple[PluginInfo, ...]:
    return kernel.discover(namespace=__name__)


__all__ = ["discover"]
