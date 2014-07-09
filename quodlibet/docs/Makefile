RTD_OVERRIDE=-Dhtml_theme=_rtd_theme -Dhtml_theme_path=.

all:
	sphinx-build -b html -n . _build_all

guide:
	sphinx-build -b html -c . -n guide _build_guide

clean:
	rm -rf _build_all _build_guide _rtd_theme_repo _rtd_theme

_rtd_theme_repo:
	git clone https://github.com/snide/sphinx_rtd_theme.git _rtd_theme_repo

_rtd_theme: _rtd_theme_repo
	ln -s _rtd_theme_repo/sphinx_rtd_theme _rtd_theme

all_rtd: _rtd_theme
	sphinx-build $(RTD_OVERRIDE) -b html -n . _build_all

guide_rtd: _rtd_theme
	sphinx-build $(RTD_OVERRIDE) -b html -n guide _build_guide

.PHONY: clean all guide
