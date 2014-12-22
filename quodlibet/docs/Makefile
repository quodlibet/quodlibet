RTD_OVERRIDE=-Dhtml_theme=_rtd_theme -Dhtml_theme_path=.

all: _rtd_theme
	sphinx-build $(RTD_OVERRIDE) -b html -n . _build_all

guide:
	sphinx-build $(RTD_OVERRIDE) -b html -c . -n guide _build_guide

clean:
	rm -rf _build_all _build_guide _rtd_theme

.PHONY: clean guide

_rtd_theme:
	wget https://github.com/snide/sphinx_rtd_theme/archive/master.tar.gz
	tar --strip-components=1 -zxvf master.tar.gz sphinx_rtd_theme-master/sphinx_rtd_theme
	mv sphinx_rtd_theme _rtd_theme
	rm master.tar.gz
