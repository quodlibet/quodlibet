SOURCE=favicon.svg
DEST=favicon.ico

all: $(DEST)

favicon-16.png: $(SOURCE)
	inkscape $(SOURCE) --export-png $@ -w 16 -h 16

favicon-24.png: $(SOURCE)
	inkscape $(SOURCE) --export-png $@ -w 24 -h 24

favicon-32.png: $(SOURCE)
	inkscape $(SOURCE) --export-png $@ -w 32 -h 32

favicon-48.png: $(SOURCE)
	inkscape $(SOURCE) --export-png $@ -w 48 -h 48

favicon-64.png: $(SOURCE)
	inkscape $(SOURCE) --export-png $@ -w 64 -h 64

$(DEST): favicon-16.png favicon-24.png favicon-32.png favicon-48.png favicon-64.png
	convert favicon-16.png favicon-24.png favicon-32.png favicon-48.png favicon-64.png $(DEST)
	rm favicon-16.png favicon-24.png favicon-32.png favicon-48.png favicon-64.png

.PHONY: clean

clean:
	rm -f favicon-16.png favicon-24.png favicon-32.png favicon-48.png favicon-64.png favicon.ico
