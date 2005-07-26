top_srcdir = ../
NAME = quodlibet
ALL_LINGUAS = en_GB en_CA de pl ru fr fi nl he
PO_DIR ?= $(PREFIX)/usr/share/locale

all:

po: quodlibet.pot
	for F in $(ALL_LINGUAS); do make $$F.mo; done

quodlibet.pot: ../quodlibet.py ../library.py tag-names.py ../util.py ../widgets.py ../exfalso.py ../formats/audio.py ../plugins.py ../qltk.py
	intltool-update --pot --gettext-package=$(NAME)

%.po: quodlibet.pot
	intltool-update --gettext-package=$(NAME) `echo $@ | sed s/.po//`

%.mo: %.po quodlibet.pot
	msgfmt -o $@ $<

clean:
	rm -f untitled.pot

mo-clean: distclean
	rm -f *.mo quodlibet.pot quodlibet.gmo

distclean: clean
	rm -f *~

install-po:
	for F in $(ALL_LINGUAS); do mkdir -p $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES && install -m 644 $$F.mo $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES/$(NAME).mo; done
