Quod Libet / Ex Falso Documentation
===================================

Dependencies:

* sphinx (http://sphinx-doc.org/)

Development:

make watch
    Start a server and auto rebuild on changes

Build:

make
    Build full documentation

make guide
    Build only the user guide

../setup.py build_sphinx
    Build the user guide and put it into ``../build/sphinx``.
    This is meant for packagers who want to ship and install the user guide.
