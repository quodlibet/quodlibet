#!/usr/bin/python
# Very simple FLAC player using the FLAC FileDecoder and libao

import flac.decoder as decoder
import flac.metadata as metadata
import ao
import sys

# setup libao audio device
#id = ao.driver_id('esd')
#id = ao.driver_id('alsa09')
id = ao.driver_id('oss')
ao = ao.AudioDevice(id)

# write our callbacks (in Python!!)
def metadata_callback(dec, block):
    if block.type == metadata.VORBIS_COMMENT:
        # use flac.metadata to access vorbis comments!
        vc = metadata.VorbisComment(block)
        print vc.vendor_string
        for k in vc.comments:
            print '%s=%s' % (k, vc.comments[k])

def error_callback(dec, status):
    pass

def write_callback(dec, buff, size):
    # print dec.get_decode_position()
    ao.play(buff, size)
    return decoder.FLAC__FILE_DECODER_OK

# create a new file decoder
mydec = decoder.FileDecoder()

# set some properties
mydec.set_md5_checking(False);
mydec.set_filename(sys.argv[1])
mydec.set_metadata_respond_all()

# set the callbacks
mydec.set_write_callback(write_callback)
mydec.set_error_callback(error_callback)
mydec.set_metadata_callback(metadata_callback)

# initialise, process metadata
mydec.init()
mydec.process_until_end_of_metadata()

# print out some stats, have to decode some data first
mydec.process_single()
print 'Channels: %d' % mydec.get_channels()
print 'Bits Per Sample: %d' % mydec.get_bits_per_sample()
print 'Sample Rate: %d' % mydec.get_sample_rate()
print 'BlockSize: %d' % mydec.get_blocksize()

# play the rest of the file
mydec.process_until_end_of_file()

# cleanup
mydec.finish()
