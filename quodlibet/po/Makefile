top_srcdir = ../
NAME = quodlibet
ALL_LINGUAS = en_GB en_CA de pl ru fr
PO_DIR ?= /usr/share/locale

all:

po: quodlibet.pot
	for F in $(ALL_LINGUAS); do make $$F.mo; done

quodlibet.pot: ../quodlibet.py ../library.py tag-names.py ../util.py ../widgets.py ../exfalso.py ../formats/audio.py
	intltool-update --pot --gettext-package=$(NAME)

%.mo: %.po quodlibet.pot
	intltool-update --gettext-package=$(NAME) `echo $< | sed s/.po//`
	msgfmt -o $@ $<

clean:
	rm -f untitled.pot

distclean: clean
	rm -f *~

install-po:
	for F in $(ALL_LINGUAS); do mkdir -p $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES && install -m 644 $$F.mo $(DESTDIR)$(PO_DIR)/$$F/LC_MESSAGES/$(NAME).mo; done
