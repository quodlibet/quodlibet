# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL v2.

all: build

modplug.so: modplug.c build
	cp build/lib*/modplug.so .

build: modplug.c
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist
	rm -f modplug.so

distclean: clean
	rm -f *~
