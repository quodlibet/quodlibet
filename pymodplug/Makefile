# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL v2.

all: build

build: modplug.py
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist

distclean: clean
	rm -f *~ *.pyc
