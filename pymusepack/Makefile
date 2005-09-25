all: musepack/mpc.py musepack/apev2.py

build:
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist
	rm -f */*.pyc

distclean: clean
	rm -f *~ */*~

test: musepack/mpc.py musepack/apev2.py
	@python -c "import tests; tests.unit()"
