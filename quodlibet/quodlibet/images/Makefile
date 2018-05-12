THEME=hicolor

QL_SOURCE=$(THEME)/scalable/apps/io.github.quodlibet.QuodLibet.svg
QL_DEST=io.github.quodlibet.QuodLibet.png

EF_SOURCE=$(THEME)/scalable/apps/exfalso.svg
EF_DEST=exfalso.png

QL_MC_SOURCE=$(THEME)/scalable/status/quodlibet-missing-cover.svg
QL_MC_DEST=quodlibet-missing-cover.png

PNG16_APPS_DIR=$(THEME)/16x16/apps
PNG16_STATUS_DIR=$(THEME)/16x16/status
PNG16_QL_DEST=$(PNG16_APPS_DIR)/$(QL_DEST)
PNG16_EF_DEST=$(PNG16_APPS_DIR)/$(EF_DEST)
PNG16_MC_DEST=$(PNG16_STATUS_DIR)/$(QL_MC_DEST)

PNG24_APPS_DIR=$(THEME)/24x24/apps
PNG24_STATUS_DIR=$(THEME)/24x24/status
PNG24_QL_DEST=$(PNG24_APPS_DIR)/$(QL_DEST)
PNG24_EF_DEST=$(PNG24_APPS_DIR)/$(EF_DEST)
PNG24_MC_DEST=$(PNG24_STATUS_DIR)/$(QL_MC_DEST)

PNG32_APPS_DIR=$(THEME)/32x32/apps
PNG32_STATUS_DIR=$(THEME)/32x32/status
PNG32_QL_DEST=$(PNG32_APPS_DIR)/$(QL_DEST)
PNG32_EF_DEST=$(PNG32_APPS_DIR)/$(EF_DEST)
PNG32_MC_DEST=$(PNG32_STATUS_DIR)/$(QL_MC_DEST)

PNG48_APPS_DIR=$(THEME)/48x48/apps
PNG48_STATUS_DIR=$(THEME)/48x48/status
PNG48_QL_DEST=$(PNG48_APPS_DIR)/$(QL_DEST)
PNG48_EF_DEST=$(PNG48_APPS_DIR)/$(EF_DEST)
PNG48_MC_DEST=$(PNG48_STATUS_DIR)/$(QL_MC_DEST)

PNG64_APPS_DIR=$(THEME)/64x64/apps
PNG64_STATUS_DIR=$(THEME)/64x64/status
PNG64_QL_DEST=$(PNG64_APPS_DIR)/$(QL_DEST)
PNG64_EF_DEST=$(PNG64_APPS_DIR)/$(EF_DEST)
PNG64_MC_DEST=$(PNG64_STATUS_DIR)/$(QL_MC_DEST)

PNG256_APPS_DIR=$(THEME)/256x256/apps
PNG256_STATUS_DIR=$(THEME)/256x256/status
PNG256_QL_DEST=$(PNG256_APPS_DIR)/$(QL_DEST)
PNG256_EF_DEST=$(PNG256_APPS_DIR)/$(EF_DEST)
PNG256_MC_DEST=$(PNG256_STATUS_DIR)/$(QL_MC_DEST)

SYMBOLIC_SRC=$(wildcard $(THEME)/scalable/apps/*.svg.in)
SYMBOLIC_TARGET=$(SYMBOLIC_SRC:.svg.in=.svg)

all: png16 png24 png32 png48 png64 png256 $(SYMBOLIC_TARGET)

png16: $(PNG16_QL_DEST) $(PNG16_EF_DEST) $(PNG16_MC_DEST)

png24: $(PNG24_QL_DEST) $(PNG24_EF_DEST) $(PNG24_MC_DEST)

png32: $(PNG32_QL_DEST) $(PNG32_EF_DEST) $(PNG32_MC_DEST)

png48: $(PNG48_QL_DEST) $(PNG48_EF_DEST) $(PNG48_MC_DEST)

png64: $(PNG64_QL_DEST) $(PNG64_EF_DEST) $(PNG64_MC_DEST)

png256: $(PNG256_QL_DEST) $(PNG256_EF_DEST) $(PNG256_MC_DEST)

$(SYMBOLIC_TARGET): $(SYMBOLIC_SRC)
	cp $(@:.svg=.svg.in) "_temp.svg"
	inkscape -f "_temp.svg" --verb=EditSelectAll \
		--verb=SelectionUnGroup --verb=StrokeToPath --verb=SelectionUnion \
		--verb=FileVacuum \
		--verb=FileSave --verb=FileClose --verb=FileQuit
	mv "_temp.svg" "$@"

$(PNG16_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG16_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG16_QL_DEST) -w 16 -h 16 ;

$(PNG16_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG16_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG16_EF_DEST) -w 16 -h 16 ;

$(PNG16_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG16_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG16_MC_DEST) -w 16 -h 16 ;

$(PNG24_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG24_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG24_QL_DEST) -w 24 -h 24 ;

$(PNG24_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG24_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG24_EF_DEST) -w 24 -h 24 ;

$(PNG24_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG24_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG24_MC_DEST) -w 24 -h 24 ;

$(PNG32_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG32_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG32_QL_DEST) -w 32 -h 32 ;

$(PNG32_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG32_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG32_EF_DEST) -w 32 -h 32 ;

$(PNG32_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG32_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG32_MC_DEST) -w 32 -h 32 ;

$(PNG48_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG48_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG48_QL_DEST) -w 48 -h 48 ;

$(PNG48_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG48_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG48_EF_DEST) -w 48 -h 48 ;

$(PNG48_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG48_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG48_MC_DEST) -w 48 -h 48 ;

$(PNG64_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG64_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG64_QL_DEST) -w 64 -h 64 ;

$(PNG64_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG64_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG64_EF_DEST) -w 64 -h 64 ;

$(PNG64_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG64_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG64_MC_DEST) -w 64 -h 64 ;

$(PNG256_QL_DEST): $(QL_SOURCE)
	mkdir -p $(PNG256_APPS_DIR) && \
	inkscape $(QL_SOURCE) --export-png $(PNG256_QL_DEST) -w 256 -h 256 ;

$(PNG256_EF_DEST): $(EF_SOURCE)
	mkdir -p $(PNG256_APPS_DIR) && \
	inkscape $(EF_SOURCE) --export-png $(PNG256_EF_DEST) -w 256 -h 256 ;

$(PNG256_MC_DEST): $(MC_SOURCE)
	mkdir -p $(PNG256_STATUS_DIR) && \
	inkscape $(QL_MC_SOURCE) --export-png $(PNG256_MC_DEST) -w 256 -h 256 ;

.PHONY: clean

clean:
	rm -f -R $(THEME)/16x16 $(THEME)/24x24 $(THEME)/32x32 $(THEME)/48x48 \
		$(THEME)/64x64 $(THEME)/256x256 $(SYMBOLIC_TARGET)
