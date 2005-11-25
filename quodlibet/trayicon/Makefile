# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL.

trayicon.so: build
	cp build/lib*/trayicon.so .

build: trayicon.c
	./setup.py build

DEFS=`pkg-config --variable=defsdir pygtk-2.0`

trayicon.c: trayicon.defs trayicon.override
	pygtk-codegen-2.0 --prefix trayicon \
	/usr/share/pygtk/2.0/defs/gdk-types.defs \
	/usr/share/pygtk/2.0/defs/gtk-types.defs \
	--override trayicon.override \
	trayicon.defs > gen-tmp
	mv gen-tmp $@

clean:
	rm -f trayicon.so *.o trayicon.c
	rm -rf build dist

distclean: clean
	rm -f *~ gen-tmp
