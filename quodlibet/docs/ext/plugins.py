from docutils.parsers.rst import Directive
from docutils import nodes
from quodlibet.util import get_module_dir
from quodlibet.util.modulescanner import ModuleScanner
from quodlibet.plugins import list_plugins, Plugin
import quodlibet
import os


class PluginsDirective(Directive):

    has_content = True

    def get_plugins(self):
        # Most of this code is copied directly from tests/plugin/__init__.py
        # Consider moving this to a function that both can call instead
        PLUGIN_DIRS = []

        root = os.path.join(get_module_dir(quodlibet), "ext")
        for entry in os.listdir(root):
            if entry.startswith("_"):
                continue
            path = os.path.join(root, entry)
            if not os.path.isdir(path):
                continue
            PLUGIN_DIRS.append(path)

        ms = ModuleScanner(PLUGIN_DIRS)
        ms.rescan()

        plugins = []
        for name, module in ms.modules.items():
            for plugin in list_plugins(module.module):
                plugins.append(Plugin(plugin))

        return plugins

    def run(self):
        plugins = self.get_plugins()
        output = []

        for plugin in sorted(plugins, key=lambda p: p.name):
            title = nodes.title(text=plugin.name)
            par = nodes.paragraph(text=plugin.description)

            section = nodes.section()
            section['ids'].append(plugin.id)
            section += title
            section += par
            output.append(section)

        return output


def setup(app):
    app.add_directive('plugins', PluginsDirective)
