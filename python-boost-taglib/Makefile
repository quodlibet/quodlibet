all:
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist *.so

distclean: clean
	rm -f *~ */*~
