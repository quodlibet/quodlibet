MODULES = config.py library.py match.py parser.py player.py util.py

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
	install -m 644 $(NAME).png $(DESTDIR)$(PREFIX)/share/pixmaps
	install -m 644 $(NAME).desktop $(DESTDIR)$(PREFIX)/share/applications
	ln -sf ../$(TO)/$(NAME).py $(DESTDIR)$(PREFIX)/bin/$(NAME)
	(test -e statusicon.so && install -m 755 statusicon.so $(DESTDIR)$(PREFIX)/$(TO)) || /bin/true
	(test -e mmkeys.so && install -m 755 mmkeys.so $(DESTDIR)$(PREFIX)/$(TO)) || /bin/true

clean:
	rm -f *.pyc */*.pyc $(NAME).zip statusicon.so mmkeys.so
	rm -f messages.pot quodlibet.glade.h
	cd statusicon && make clean
	cd mmkeys && make clean

distclean: clean
	rm -f *~ \#* *.bak *.orig */*~ */\#* */*.bak */*.orig $(NAME).gladep

extensions: statusicon.so mmkeys.so

statusicon.so:
	cd statusicon && make && cd ..
	cp statusicon/statusicon.so .

mmkeys.so:
	cd mmkeys && make && cd ..
	cp mmkeys/mmkeys.so .

test:
	python -c "import tests; tests.unit()"

messages.pot: quodlibet.glade.h quodlibet.py library.py
	xgettext -k_ -kN_ -o $@ quodlibet.glade.h quodlibet.py library.py

quodlibet.glade.h:
	intltool-extract --type=xml/glade > $@
