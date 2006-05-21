# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL.

mmkeys.so: build
	cp build/lib*/mmkeys.so .

build: mmkeyspy.c
	./setup.py build

DEFS=`pkg-config --variable=defsdir pygtk-2.0`

mmkeyspy.c: mmkeys.defs mmkeys.override
	pygtk-codegen-2.0 --prefix mmkeys \
	--register $(DEFS)/gdk-types.defs \
	--register $(DEFS)/gtk-types.defs \
	--override mmkeys.override \
	mmkeys.defs > gen-tmp
	mv gen-tmp $@

clean:
	rm -f mmkeys.so *.o mmkeyspy.c
	rm -rf build dist

distclean: clean
	rm -f *~ gen-tmp
