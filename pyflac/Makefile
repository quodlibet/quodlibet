PYTHON_DIR	= /usr/include/python2.3
CFLAGS 		= -fPIC -shared -g -I$(PYTHON_DIR) -lFLAC

all: sw_metadata decoder encoder

sw_metadata: flac/sw_metadata.py flac/_sw_metadata.so

decoder: flac/decoder.py flac/_decoder.so

encoder: flac/encoder.py flac/_encoder.so

%.py %_wrap.c: %.i flac/format.i
	swig -python $<

flac/_%.so: flac/%_wrap.c
	$(CC) $(CFLAGS) $< -o $@

clean:
	rm -f flac/*.so flac/*_wrap.c
	rm -f flac/sw_metadata.py flac/decoder.py flac/encoder.py

distclean: clean
	rm -f */*~ *~
