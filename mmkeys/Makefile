# Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL.

PYTHON_DIR = /usr/include/python2.3/

CFLAGS = -O2 `pkg-config --cflags gtk+-2.0 pygtk-2.0` -I$(PYTHON_DIR)
LDFLAGS = `pkg-config --libs gtk+-2.0 pygtk-2.0`

mmkeys.so: mmkeyspy.o mmkeys.o mmkeysmodule.o
	$(CC) $(LDFLAGS) -shared $^ -o $@

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

distclean: clean
	rm -f *~ gen-tmp
