INCL 	= -I/usr/include/python2.3 
LIBS	= -lFLAC

all:	sw_metadata decoder encoder

decoder:	flac/decoder.py flac/_decoder.so

encoder:	flac/encoder.py flac/_encoder.so

sw_metadata:	flac/sw_metadata.py flac/_sw_metadata.so

flac/sw_metadata.py flac/_sw_metadata.so:	flac/sw_metadata.i flac/format.i
	swig -python flac/sw_metadata.i
	$(CC) -g $(INCL) flac/sw_metadata_wrap.c -shared $(LIBS) -o flac/_sw_metadata.so

flac/decoder.py flac/_decoder.so:	flac/decoder.i flac/format.i
	swig -python flac/decoder.i
	$(CC) -g $(INCL) flac/decoder_wrap.c -shared $(LIBS) -o flac/_decoder.so

flac/encoder.py flac/_encoder.so:	flac/encoder.i flac/format.i
	swig -python flac/encoder.i
	$(CC) -g $(INCL) flac/encoder_wrap.c -shared $(LIBS) -o flac/_encoder.so

clean:
	rm -f flac/sw_metadata_wrap.c flac/_sw_metadata.so flac/sw_metadata.py
	rm -f flac/decoder_wrap.c flac/_decoder.so flac/decoder.py
	rm -f flac/encoder_wrap.c flac/_encoder.so flac/encoder.py
