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
	ln -sf ../$(TO)/$(NAME).py $(DESTDIR)$(PREFIX)/bin/$(NAME)
	(test -e statusicon.so && install -m 755 statusicon.so $(DESTDIR)$(PREFIX)/$(TO)) || /bin/true

clean:
	rm -f *.pyc */*.pyc $(NAME).zip statusicon.so
	cd statusicon && make clean

distclean: clean
	rm -f *~ \#* *.bak *.orig */*~ */\#* */*.bak */*.orig

statusicon.so:
	cd statusicon && make && cd ..
	cp statusicon/statusicon.so .

test:
	python -c "import tests; tests.unit()"
