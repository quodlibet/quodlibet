all: exfalso.1 quodlibet.1 operon.1

setup:
	mkdir -p _man

%.1:%.rst setup
	rst2man $< > _man/$@

.PHONY: setup
