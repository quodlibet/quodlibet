all:
	sphinx-build -b html -n . _build_all

guide:
	sphinx-build -b html -c . -n guide _build_guide

clean:
	rm -rf _build_all _build_guide

.PHONY: clean guide show linkcheck

show: all
	xdg-open _build_all/index.html

linkcheck:
	sphinx-build -b linkcheck -n . _build_all
