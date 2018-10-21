from docutils.parsers.rst import Directive
from docutils import nodes
import re
import os


class PluginsDirective(Directive):

    has_content = True

    def get_plugins(self):
        plugins = []
        dir_ = self.state.document.settings.env.config.dir_

        for root, dirs, files in os.walk(os.path.join(dir_, '..', 'quodlibet', 'ext')):
            for filename in files:
                if filename[-3:] == '.py':
                    path = os.path.join(root, filename)
                    with open(path, 'r') as f:
                        cont = f.read()
                        ids = re.findall(r'PLUGIN_ID = "(.+?)"', cont)
                        names = re.findall(r'PLUGIN_NAME = _\("(.+?)"\)', cont)
                        raw_descs = re.findall(r'PLUGIN_DESC = _\("((.|\n)+?)"\)', cont)
                        descs = []
                        for desc in raw_descs:
                            new_desc = ''.join([s.strip(' ').strip('"') for s in desc[0].split('\n')])
                            descs.append(new_desc)

                        if len(ids) > 0 and len(ids) == len(names) == len(descs):
                            for i in range(len(ids)):
                                plugins.append((ids[i], names[i], descs[i]))
        return plugins

    def run(self):
        plugins = self.get_plugins()
        output = []

        for ID, name, desc in sorted(plugins, key=lambda p: p[1]):
            title = nodes.title(text=name)
            par = nodes.paragraph(text=desc)

            section = nodes.section()
            section['ids'].append(ID)
            section += title
            section += par
            output.append(section)

        return output


def setup(app):
    app.add_directive('plugins', PluginsDirective)
