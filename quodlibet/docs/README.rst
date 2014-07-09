Quod Libet / Ex Falso Documentation
===================================

Dependencies:

* sphinx (http://sphinx-doc.org/)

Build:

make
    Build full documentation

make guide
    Build only the user guide

make all_rtd
    Build full documentation using the rtfd.org theme

make guide_rtd
    Build only the user guide using the rtfd.org theme

setup.py build_sphinx
    Build the user guide and put it into ``build/sphinx``.
    This is meant for packagers who want to ship and install the user guide.
