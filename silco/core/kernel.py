class SilcoKernel:
    def __init__(self):
        self.plugins = {
            "shapes": {},
            "renderers": {},
            "layouts": {}
        }

    def register(self, plugin_type, name, plugin):
        if plugin_type not in self.plugins:
            raise ValueError(f"Unknown plugin type: {plugin_type}")
        self.plugins[plugin_type][name] = plugin

    def get(self, plugin_type, name):
        return self.plugins[plugin_type][name]


kernel = SilcoKernel()
