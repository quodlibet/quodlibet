QL_SOURCE=scalable/apps/quodlibet.svg
QL_DEST=quodlibet.png

QL_SYM_SOURCE=scalable/apps/quodlibet-symbolic.svg
QL_SYM_DEST=quodlibet-symbolic.png

QL_MISSING_COVER_SOURCE=scalable/status/quodlibet-missing-cover.svg
QL_MISSING_COVER_DEST=quodlibet-missing-cover.png

EF_SOURCE=scalable/apps/exfalso.svg
EF_DEST=exfalso.png

EF_SYM_SOURCE=scalable/apps/exfalso-symbolic.svg
EF_SYM_DEST=exfalso-symbolic.png

APPS_DIR=16x16/apps 24x24/apps 32x32/apps 48x48/apps 64x64/apps
STATUS_DIR=16x16/status 24x24/status 32x32/status 48x48/status 64x64/status

all: mkdestdir png16 png24 png32 png48 png64

png16: $(QL_SOURCE) $(EF_SOURCE)
	inkscape $(QL_SOURCE) --export-png 16x16/apps/$(QL_DEST) -w 16 -h 16 ;
	inkscape $(EF_SOURCE) --export-png 16x16/apps/$(EF_DEST) -w 16 -h 16 ;
	inkscape $(QL_SYM_SOURCE) --export-png 16x16/apps/$(QL_SYM_DEST) \
		-w 16 -h 16 ;
	inkscape $(EF_SYM_SOURCE) --export-png 16x16/apps/$(EF_SYM_DEST) \
		-w 16 -h 16 ;
	inkscape $(QL_MISSING_COVER_SOURCE) \
		--export-png 16x16/status/$(QL_MISSING_COVER_DEST) -w 16 -h 16

png24: $(QL_SOURCE) $(EF_SOURCE)
	inkscape $(QL_SOURCE) --export-png 24x24/apps/$(QL_DEST) -w 24 -h 24 ;
	inkscape $(EF_SOURCE) --export-png 24x24/apps/$(EF_DEST) -w 24 -h 24 ;
	inkscape $(QL_SYM_SOURCE) --export-png 24x24/apps/$(QL_SYM_DEST) \
		-w 24 -h 24 ;
	inkscape $(EF_SYM_SOURCE) --export-png 24x24/apps/$(EF_SYM_DEST) \
		-w 24 -h 24 ;
	inkscape $(QL_MISSING_COVER_SOURCE) \
		--export-png 24x24/status/$(QL_MISSING_COVER_DEST) -w 24 -h 24

png32: $(QL_SOURCE) $(EL_SOURCE)
	inkscape $(QL_SOURCE) --export-png 32x32/apps/$(QL_DEST) -w 32 -h 32 ;
	inkscape $(EF_SOURCE) --export-png 32x32/apps/$(EF_DEST) -w 32 -h 32 ;
	inkscape $(QL_SYM_SOURCE) --export-png 32x32/apps/$(QL_SYM_DEST) \
		-w 32 -h 32 ;
	inkscape $(EF_SYM_SOURCE) --export-png 32x32/apps/$(EF_SYM_DEST) \
		-w 32 -h 32 ;
	inkscape $(QL_MISSING_COVER_SOURCE) \
		--export-png 32x32/status/$(QL_MISSING_COVER_DEST) -w 32 -h 32

png48: $(QL_SOURCE) $(EF_SOURCE)
	inkscape $(QL_SOURCE) --export-png 48x48/apps/$(QL_DEST) -w 48 -h 48 ;
	inkscape $(EF_SOURCE) --export-png 48x48/apps/$(EF_DEST) -w 48 -h 48 ;
	inkscape $(QL_SYM_SOURCE) --export-png 48x48/apps/$(QL_SYM_DEST) \
		-w 48 -h 48 ;
	inkscape $(EF_SYM_SOURCE) --export-png 48x48/apps/$(EF_SYM_DEST) \
		-w 48 -h 48 ;
	inkscape $(QL_MISSING_COVER_SOURCE) \
		--export-png 48x48/status/$(QL_MISSING_COVER_DEST) -w 48 -h 48

png64: $(QL_SOURCE) $(EF_SOURCE)
	inkscape $(QL_SOURCE) --export-png 64x64/apps/$(QL_DEST) -w 64 -h 64 ;
	inkscape $(EF_SOURCE) --export-png 64x64/apps/$(EF_DEST) -w 64 -h 64 ;
	inkscape $(QL_SYM_SOURCE) --export-png 64x64/apps/$(QL_SYM_DEST) \
		-w 64 -h 64 ;
	inkscape $(EF_SYM_SOURCE) --export-png 64x64/apps/$(EF_SYM_DEST) \
		-w 64 -h 64 ;
	inkscape $(QL_MISSING_COVER_SOURCE) \
		--export-png 64x64/status/$(QL_MISSING_COVER_DEST) -w 64 -h 64

mkdestdir: mkappsdir mkstatusdir

mkappsdir:
	mkdir -p $(APPS_DIR)

mkstatusdir:
	mkdir -p $(STATUS_DIR)

.PHONY: clean

clean:
	rm -R 16x16 24x24 32x32 48x48 64x64
