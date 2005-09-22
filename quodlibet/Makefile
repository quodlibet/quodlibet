MODULES = config.py const.py efwidgets.py information.py library.py match.py parser.py player.py plugins.py properties.py qltk.py songlist.py stock.py util.py widgets.py formats/*.py mutagen/*.py browsers/*.py
SUBDIRS = trayicon mmkeys po
EXTENSIONS = trayicon.so mmkeys.so
PREFIX ?= /usr/local
TO = lib/quodlibet

all:
	@/bin/echo -n "Checking for Python... "
	@which python || ( echo "Not found." && /bin/false )
	@./check.py

make-install-dirs:
	mkdir -p $(DESTDIR)$(PREFIX)/share/man/man1
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/$(TO)

install: make-install-dirs install-exfalso install-quodlibet
	./quickzip.py quodlibet.zip $(MODULES)
	install -m 644 quodlibet.zip ql-*.png $(DESTDIR)$(PREFIX)/$(TO)
	-for E in $(EXTENSIONS); do (test -e $$E && install -m 755 $$E $(DESTDIR)$(PREFIX)/$(TO)); done
	cd po && make install-po DESTDIR=$(DESTDIR)

install-%: make-install-dirs
	install -m 755 $*.py $(DESTDIR)$(PREFIX)/$(TO)
	install -m 644 $*.1 $(DESTDIR)$(PREFIX)/share/man/man1/$*.1
	install -D -m 644 $*.png $(DESTDIR)$(PREFIX)/share/pixmaps/$*.png
	install -m 644 $*.png $(DESTDIR)$(PREFIX)/$(TO)
	install -D -m 644 $*.desktop $(DESTDIR)$(PREFIX)/share/applications/$*.desktop
	ln -sf ../$(TO)/$*.py $(DESTDIR)$(PREFIX)/bin/$*

clean:
	rm -f *.pyc */*.pyc quodlibet.zip $(EXTENSIONS)
	for D in $(SUBDIRS); do cd $$D && make clean && cd ..; done

distclean: clean
	rm -f *~ */*~ \#* *.bak *.orig $(NAME).gladep
	for D in $(SUBDIRS); do cd $$D && make distclean && cd ..; done

extensions: $(EXTENSIONS)

%.so: %
	cd $^ && make $@ && cd ..
	cp $^/$@ .

po-data:
	cd po && make po
