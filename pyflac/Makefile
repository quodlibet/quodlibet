all: build

build: flac/sw_metadata_wrap.c flac/decoder_wrap.c flac/encoder_wrap.c
	./setup.py build

%_wrap.c: %.i flac/format.i
	swig -python $<

clean:
	#rm -f flac/*_wrap.c
	#rm -f flac/sw_metadata.py flac/decoder.py flac/encoder.py
	rm -rf build dist

distclean: clean
	rm -f */*~ *~ */*.pyc

install:
	./setup.py install
