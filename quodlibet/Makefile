MODULES = config.py const.py library.py gosd.py match.py parser.py player.py util.py formats/*.py
SUBDIRS = trayicon mmkeys po
EXTENSIONS = trayicon.so mmkeys.so
NAME = quodlibet
PREFIX ?= /usr/local
TO = lib/$(NAME)

all:
	@/bin/echo -n "Checking for Python... "
	@which python || ( echo "Not found." && /bin/false )
	@./check.py

install:
	mkdir -p $(DESTDIR)$(PREFIX)/share/man/man1
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/$(TO)
	./quickzip.py $(NAME).zip $(MODULES)
	install -m 755 $(NAME).py $(DESTDIR)$(PREFIX)/$(TO)
	install -m 644 $(NAME).zip $(NAME).glade *.png $(DESTDIR)$(PREFIX)/$(TO)
	install -m 644 $(NAME).1 $(DESTDIR)$(PREFIX)/share/man/man1/$(NAME).1
	install -D -m 644 $(NAME).png $(DESTDIR)$(PREFIX)/share/pixmaps/$(NAME).png
	install -D -m 644 $(NAME).desktop $(DESTDIR)$(PREFIX)/share/applications/$(NAME).desktop
	ln -sf ../$(TO)/$(NAME).py $(DESTDIR)$(PREFIX)/bin/$(NAME)
	-for E in $(EXTENSIONS); do (test -e $$E && install -m 755 $$E $(DESTDIR)$(PREFIX)/$(TO)); done
	cd po && make install-po DESTDIR=$(DESTDIR)

clean:
	rm -f *.pyc */*.pyc $(NAME).zip $(EXTENSIONS)
	for D in $(SUBDIRS); do cd $$D && make clean && cd ..; done

distclean: clean
	rm -f *~ */*~ \#* *.bak *.orig $(NAME).gladep
	for D in $(SUBDIRS); do cd $$D && make distclean && cd ..; done

extensions: $(EXTENSIONS)

%.so: %
	cd $^ && make $@ && cd ..
	cp $^/$@ .

test:
	@python -c "import tests; tests.unit()"

po-data:
	cd po && make po
