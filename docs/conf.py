# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import types
import sys

dir_ = os.path.dirname(os.path.realpath(__file__))


def exec_module(path):
    """Executes the Python file at `path` and returns it as the module"""

    # We don't care about MSYSTEM in the doc build, just unset to prevent the
    # assert in const.py
    os.environ.pop("MSYSTEM", None)
    globals_ = {}
    with open(path, encoding="utf-8") as h:
        exec(h.read(), globals_)
    module = types.ModuleType("")
    module.__dict__.update(globals_)
    return module


const = exec_module(os.path.join(dir_, "..", "quodlibet", "const.py"))

needs_sphinx = "1.3"

sys.path.append(os.path.join(dir_, "ext"))

extensions = ["sphinx.ext.autodoc", "sphinx.ext.extlinks", "contributors"]

source_suffix = ".rst"
root_doc = "index"
project = "Quod Libet"
copyright = ""
exclude_patterns = ["_build", "_build_all", "README.rst", "**/README.rst"]
html_theme = "sphinx_rtd_theme"
html_title = project
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-suppress_warnings
suppress_warnings = ["config.cache"]

extlinks = {
    "bug": ("https://github.com/quodlibet/quodlibet/issues/%s", "#%s"),
    "pr": ("https://github.com/quodlibet/quodlibet/pull/%s", "#%s"),
    "user": ("https://github.com/%s", "%s"),
}

linkcheck_anchors = True
linkcheck_workers = 20
linkcheck_ignore = [r".*groups\.google\.com/.*", r".*keyserver\.ubuntu\.com.*"]

html_context = {
    "extra_css_files": [
        "//quodlibet.github.io/fonts/font-mfizz.css",
        "_static/extra.css",
    ],
}

html_static_path = [
    "extra.css",
]

html_theme_options = {
    "display_version": False,
}

html_favicon = "favicon/favicon.ico"
html_show_copyright = False


def setup(app):
    app.add_config_value("const", const, True)
