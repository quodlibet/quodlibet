all:
	python3 -m sphinx -b html -n . _build_all

watch:
	sphinx-autobuild -b html -n . _build_all

guide:
	python3 -m sphinx -b html -c . -n guide _build_guide

clean:
	rm -rf _build_all _build_guide

.PHONY: clean guide show linkcheck

show: all
	xdg-open _build_all/index.html

linkcheck:
	python3 -m sphinx -b linkcheck -n . _build_all
