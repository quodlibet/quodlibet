#!/usr/bin/python

import flac.encoder as encoder
import flac.metadata as metadata
import wave
import sys

oldprog = 0

# progress callback
def progress(enc, bytes_written, samples_written, frames_written, total_frames_estimate):
    global oldprog
    prog = int((float(frames_written)/float(total_frames_estimate)) * 100)
    if prog != oldprog or prog == 0:
        sys.stdout.write('\b\b\b\b\b\b\b\b\b\b\b\b\b')
        sys.stdout.write("%3d%% Complete" % prog)
        sys.stdout.flush()
        oldprog = prog

wav = wave.open(sys.argv[1],'r')

# setup the encoder ...
enc = encoder.FileEncoder()
enc.set_filename(sys.argv[1]+'.flac')
enc.set_channels(wav.getnchannels())
enc.set_bits_per_sample(wav.getsampwidth()*8)
enc.set_sample_rate(wav.getframerate())
enc.set_blocksize(4608)
enc.set_do_mid_side_stereo(True)
enc.set_total_samples_estimate(wav.getnframes())
enc.set_progress_callback(progress)

# create a vorbis block
vorbis = metadata.VorbisComment()
vorbis.vendor_string = 'python-flac' # reset to default anyway I think...
vorbis.comments['TITLE'] = "My Title"
vorbis.comments['ARTIST'] = 'Me'

# a seektable with 100 points
seektbl = metadata.SeekTable()
seektbl.template_append_spaced_points(100, enc.get_total_samples_estimate())
seektbl.template_sort(True)

# add the metadata blocks
enc.set_metadata((seektbl.block, vorbis.block), 2)

# initialise
if enc.init() != encoder.FLAC__FILE_ENCODER_OK:
    print "Error"
    sys.exit()

# start encoding !
nsamples = 1024
while 1:
    data = wav.readframes(nsamples)
    if not data:
        enc.finish()
        break
    enc.process(data, nsamples)
