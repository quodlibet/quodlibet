# Set the C flags to include the GTK+ and Python libraries
CFLAGS = `pkg-config --cflags gtk+-2.0 pygtk-2.0` -I/usr/include/python2.3/ -I.
LDFLAGS = `pkg-config --libs gtk+-2.0 pygtk-2.0`

# Build the shared object
mmkeys.so: mmkeyspy.o mmkeys.o mmkeysmodule.o
	$(CC) $(LDFLAGS) -shared $^ -o $@

# The path to the GTK+ python types
DEFS=`pkg-config --variable=defsdir pygtk-2.0`

# Generate the C wrapper from the defs and our override file
mmkeyspy.c: mmkeys.defs mmkeys.override
	pygtk-codegen-2.0 --prefix mmkeys \
	--register $(DEFS)/gdk-types.defs \
	--register $(DEFS)/gtk-types.defs \
	--override mmkeys.override \
	mmkeys.defs > gen-tmp
	mv gen-tmp $@

# A rule to clean the generated files
clean:
	rm -f mmkeys.so *.o mmkeyspy.c

distclean: clean
	rm -f *~ gen-tmp
