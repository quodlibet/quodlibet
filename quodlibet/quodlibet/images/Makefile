THEME=hicolor

QL_SOURCE=$(THEME)/scalable/apps/io.github.quodlibet.QuodLibet.svg
QL_DEST=io.github.quodlibet.QuodLibet.png

EF_SOURCE=$(THEME)/scalable/apps/exfalso.svg
EF_DEST=exfalso.png

QL_MC_SOURCE=$(THEME)/scalable/status/quodlibet-missing-cover.svg
QL_MC_DEST=quodlibet-missing-cover.png

SYMBOLIC_SRC=$(wildcard $(THEME)/scalable/apps/*.svg.in)
SYMBOLIC_TARGET=$(SYMBOLIC_SRC:.svg.in=.svg)

all: \
	png-16x16 \
	png-24x24 \
	png-32x32 \
	png-48x48 \
	png-64x64 \
	png-128x128 \
	png-256x256 \
	$(SYMBOLIC_TARGET)

clean:
	rm -f -R \
		$(THEME)/16x16 \
		$(THEME)/24x24 \
		$(THEME)/32x32 \
		$(THEME)/48x48 \
		$(THEME)/64x64 \
		$(THEME)/128x128 \
		$(THEME)/256x256 \
		$(SYMBOLIC_TARGET)

png-%: $(THEME)/%/apps/$(QL_DEST) $(THEME)/%/apps/$(EF_DEST) $(THEME)/%/status/$(QL_MC_DEST)
	@true

$(THEME)/%/apps/$(QL_DEST): $(QL_SOURCE)
	mkdir -p $(dir $@)
	inkscape $< --export-png $@ -w $(shell echo $* | cut -dx -f1) -h $(shell echo $* | cut -dx -f2) ;

$(THEME)/%/apps/$(EF_DEST): $(EF_SOURCE)
	mkdir -p $(dir $@)
	inkscape $< --export-png $@ -w $(shell echo $* | cut -dx -f1) -h $(shell echo $* | cut -dx -f2) ;

$(THEME)/%/status/$(QL_MC_DEST): $(QL_MC_SOURCE)
	mkdir -p $(dir $@)
	inkscape $< --export-png $@ -w $(shell echo $* | cut -dx -f1) -h $(shell echo $* | cut -dx -f2) ;

$(SYMBOLIC_TARGET): $(SYMBOLIC_SRC)
	cp $(@:.svg=.svg.in) "_temp.svg"
	inkscape -f "_temp.svg" --verb=EditSelectAll \
		--verb=SelectionUnGroup --verb=StrokeToPath --verb=SelectionUnion \
		--verb=FileVacuum \
		--verb=FileSave --verb=FileClose --verb=FileQuit
	mv "_temp.svg" "$@"

.PRECIOUS: $(THEME)/%/apps/$(QL_DEST) $(THEME)/%/apps/$(EF_DEST) $(THEME)/%/status/$(QL_MC_DEST)
.PHONY: clean png-%
