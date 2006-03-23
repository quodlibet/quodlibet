MODULES = config.py const.py library.py massagers.py player.py stock.py widgets.py
MODULE_DIRS = browsers formats qltk parse plugins util
PROGRAMS = exfalso quodlibet
SUBDIRS = trayicon mmkeys po
EXTENSIONS = _trayicon.so _mmkeys.so
PREFIX ?= /usr/local
TO = share/quodlibet
TODEP = lib/quodlibet

all:
	@/bin/echo -n "Checking for Python... "
	@which python || ( echo "Not found." && /bin/false )
	@./check.py

make-install-dirs:
	mkdir -p $(DESTDIR)$(PREFIX)/share/man/man1
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/$(TO)

# Failure to build POT/MO files is non-fatal in case there is a clock
# skew on the user's system and they don't have intltool/gettext installed;
# then at least the QL install will not fail mysteriously, it will just
# have (potentially) outdated translations. Ideally any developers
# installing the SVN version will have intltool and so it will build fine.
install: make-install-dirs install-dirs install-programs
	install -m 644 $(MODULES) rhythmbox-*.png $(DESTDIR)$(PREFIX)/$(TO)
	-for E in $(EXTENSIONS); do (test -e $$E && install -m 755 -D $$E $(DESTDIR)$(PREFIX)/$(TODEP)/$$E); done
	-cd po && make install-po DESTDIR=$(DESTDIR)

install-dirs: $(addprefix dir-install-, $(MODULE_DIRS))

install-programs: $(addprefix app-install-, $(PROGRAMS))

dir-install-%: make-install-dirs
	mkdir -p $(DESTDIR)$(PREFIX)/$(TO)/$*
	install -m 644 $*/*.py $(DESTDIR)$(PREFIX)/$(TO)/$*

app-install-%: make-install-dirs %.desktop
	install -m 755 $*.py $(DESTDIR)$(PREFIX)/$(TO)
	install -m 644 $*.1 $(DESTDIR)$(PREFIX)/share/man/man1/$*.1
	install -D -m 644 $*.png $(DESTDIR)$(PREFIX)/share/pixmaps/$*.png
	install -m 644 $*.svg $*.png $(DESTDIR)$(PREFIX)/$(TO)
	-install -D -m 644 $*.desktop $(DESTDIR)$(PREFIX)/share/applications/$*.desktop
	ln -sf ../$(TO)/$*.py $(DESTDIR)$(PREFIX)/bin/$*

clean:
	rm -f *.pyc */*.pyc $(EXTENSIONS) messages.mo
	for D in $(SUBDIRS); do cd $$D && make clean && cd ..; done

distclean: clean
	rm -f *~ */*~ \#* */\#* *.bak */*.bak *.orig */*.orig
	for D in $(SUBDIRS); do cd $$D && make distclean && cd ..; done

superclean: distclean
	rm -f *.desktop
	cd po && make mo-clean

extensions: $(EXTENSIONS)

_trayicon.so:
	cd trayicon && make trayicon.so && cd ..
	cp trayicon/trayicon.so _trayicon.so
_mmkeys.so:
	cd mmkeys && make mmkeys.so && cd ..
	cp mmkeys/mmkeys.so _mmkeys.so

po-data:
	cd po && make po

%.desktop: %.desktop.in po/*.po
	-intltool-merge -d po $< $@

.PHONY: all make-install-dirs install install-% clean distclean po-data
