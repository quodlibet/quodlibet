all: mp4info/mp4.so

mp4info/mp4.so: build
	cp build/lib*/mp4info/mp4.so mp4info

build: mp4info/mp4.c
	./setup.py build

install: build
	./setup.py install

clean:
	./setup.py clean
	rm -rf build dist
	rm -f mp4info/mp4.so
	rm -f */*.pyc

distclean: clean
	rm -f *~ */*~
