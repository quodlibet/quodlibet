top_srcdir = ../
NAME = quodlibet
ALL_LINGUAS = en_GB en_CA de pl ru fr fi nl he bg gl it es pt ko lt nb \
              sk sv zh_CN hu ja zh_TW ro
PREFIX ?= /usr
PO_DIR ?= $(PREFIX)/share/locale

all:

po: $(addsuffix .mo, $(ALL_LINGUAS))

quodlibet.pot: POTFILES.in ../*.py ../formats/*.py ../browsers/*.py ../qltk/*.py ../plugins/*.py tag-names.py ../util/*.py ../library/*.py ../devices/*.py
	intltool-update --pot --gettext-package=$(NAME)

%.po: quodlibet.pot
	intltool-update --dist --gettext-package=$(NAME) $*

%.mo: %.po
	msgfmt -o $@ $<

check: $(addprefix check-, $(ALL_LINGUAS))

check-%: %.po
	msgfmt -c $<

clean:
	rm -f untitled.pot messages.mo quodlibet.gmo notexist missing
	rm -f *.mo

distclean: clean
	rm -f *~

install-po: po
	for F in $(ALL_LINGUAS); do mkdir -p $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES && install -m 644 $$F.mo $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES/$(NAME).mo; done

.PHONY: po check check-% clean mo-clean distclean install-po
