# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL.

statusicon.so: build
	cp build/lib*/statusicon.so .

build: statusicon.c eggmarshalers.h eggmarshalers.c
	./setup.py build

DEFS=`pkg-config --variable=defsdir pygtk-2.0`

statusicon.c: statusicon.defs statusicon.override
	pygtk-codegen-2.0 --prefix statusicon \
	--register $(DEFS)/gdk-types.defs \
	--register $(DEFS)/gtk-types.defs \
	--override statusicon.override \
	statusicon.defs > gen-tmp
	mv gen-tmp $@

eggmarshalers.h: eggmarshalers.list
	glib-genmarshal --prefix=_egg_marshal eggmarshalers.list --header > gen-tmp
	mv gen-tmp $@

eggmarshalers.c: eggmarshalers.list
	glib-genmarshal --prefix=_egg_marshal eggmarshalers.list --body > gen-tmp
	mv gen-tmp $@

clean:
	rm -f statusicon.so *.o statusicon.c eggmarshalers.[ch]
	rm -rf build dist

distclean: clean
	rm -f *~ gen-tmp
