top_srcdir = ../
NAME = quodlibet
ALL_LINGUAS = en_GB en_CA
PO_DIR ?= /usr/share/locale

all: quodlibet.pot
	for F in $(ALL_LINGUAS); do make $$F.mo; done

quodlibet.pot: ../quodlibet.glade ../quodlibet.py ../library.py ../pmp.py tag-names.py
	intltool-update --pot --gettext-package=$(NAME)

%.mo: %.po quodlibet.pot
	intltool-update --gettext-package=$(NAME) `echo $< | sed s/.po//`
	msgfmt -o $@ $<

clean:
	rm -f quodlibet.pot quodlibet.glade.h *.mo
	for F in $(ALL_LINGUAS); do rm -rf $$F; done

distclean: clean
	rm -f *~

install-po:
	for F in $(ALL_LINGUAS); do mkdir -p $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES && install -m 644 $$F.mo $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES/$(NAME).mo; done
