# Set the C flags to include the GTK+ and Python libraries
CFLAGS = `pkg-config --cflags gtk+-2.0 pygtk-2.0` -I/usr/include/python2.3/ -I.
LDFLAGS = `pkg-config --libs gtk+-2.0 pygtk-2.0`

# Build the shared object
statusicon.so: statusicon.o eggstatusicon.o eggtrayicon.o statusiconmodule.o eggmarshalers.o
	$(CC) $(LDFLAGS) -shared $^ -o $@

statusicon.o: eggmarshalers.h eggmarshalers.o

eggmarshalers.h: eggmarshalers.list
	glib-genmarshal --prefix=_egg_marshal eggmarshalers.list --header > gen-tmp
	mv gen-tmp $@

eggmarshalers.c: eggmarshalers.list
	glib-genmarshal --prefix=_egg_marshal eggmarshalers.list --body > gen-tmp
	mv gen-tmp $@

# The path to the GTK+ python types
DEFS=`pkg-config --variable=defsdir pygtk-2.0`

# Generate the C wrapper from the defs and our override file
statusicon.c: statusicon.defs statusicon.override
	pygtk-codegen-2.0 --prefix statusicon \
	--register $(DEFS)/gdk-types.defs \
	--register $(DEFS)/gtk-types.defs \
	--override statusicon.override \
	statusicon.defs > gen-tmp
	mv gen-tmp $@

# A rule to clean the generated files
clean:
	rm -f statusicon.so *.o statusicon.c eggmarshalers.c eggmarshalers.h gen-tmp

distclean: clean
	rm -f *~ gen-tmp
