all: musepack/mpc.so

musepack/mpc.so: build
	cp build/lib*/musepack/mpc.so musepack

build: musepack/mpc.c
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist
	rm -f musepack/mpc.so

distclean: clean
	rm -f *~ */*~
