top_srcdir = ../
NAME = quodlibet
ALL_LINGUAS =

all: quodlibet.pot
	for L in $(ALL_LINGUAS); \
	   do intltool-update --gettext-package=$(NAME) $$L && make $$L.mo; \
	done

quodlibet.pot: ../quodlibet.glade ../quodlibet.py ../library.py
	intltool-update --pot --gettext-package=$(NAME)

%.mo: %.po
	msgfmt -o $@ $<

clean:
	rm -f quodlibet.pot quodlibet.glade.h *.mo

distclean: clean
	rm -f *~
