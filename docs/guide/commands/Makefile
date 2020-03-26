MANDIR=../../../data

all: $(MANDIR)/exfalso.1 $(MANDIR)/quodlibet.1 $(MANDIR)/operon.1

$(MANDIR)/%.1:%.rst
	rst2man $< > $@
