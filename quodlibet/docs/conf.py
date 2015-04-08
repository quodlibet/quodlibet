# -*- coding: utf-8 -*-

import os
import sys

dir_ = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, dir_)
sys.path.insert(0, os.path.abspath(os.path.join(dir_, "..")))
from quodlibet import const

extensions = ['sphinx.ext.autodoc', 'ext']
source_suffix = '.rst'
master_doc = 'index'
project = 'Ex Falso / Quod Libet'
copyright = "2004-2015 %s and more" % ", ".join(const.MAIN_AUTHORS)
version = ".".join(const.VERSION.rsplit(".")[:2])
release = const.VERSION
if release.endswith(".-1"):
    release = release[:-3]
exclude_patterns = ['_build', '_rtd_theme_repo', 'README.rst']
html_theme = "haiku"
html_title = "%s (%s)" % (project, version)
bug_url_template = "https://github.com/quodlibet/quodlibet/issues/%s"

RTD_NEW_THEME = True

# on a stable branch which isn't a release
if const.BRANCH_NAME != "master" and const.VERSION_TUPLE[-1] == -1:
    rst_prolog = """

.. note::
    There exists a newer version of this page and the content below may be 
    outdated. See %s for the latest documentation.

""" % (const.DOCS_LATEST)
