# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL v2.

all: build modplug.so

modplug.so: modplug.c build
	mv build/lib*/modplug.so .

build: modplug.c
	./setup.py build

clean:
	./setup.py clean
	rm -rf build
	rm -f modplug.so

distclean: clean
	rm -f *~
