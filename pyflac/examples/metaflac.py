#!/usr/bin/python
# Example of using the flac.metadata python bindings.
# It is designed to me somewhat like the 'metaflac' command.

#import flac.metaflac as metadata
import flac.metadata as metadata
import sys

try:
    fname = sys.argv[1]
except IndexError:
    fname = 'fao.flac'

# create a chain
chain = metadata.Chain()
chain.read(fname)

# get iterator, initialise
it = metadata.Iterator()
it.init(chain)

cur_block = 0;
while 1:
    block = it.get_block()
    # print some common fields
    print 'METADATA BLOCK #%d' % cur_block
    print '  type: %d (%s)' % (block.type, metadata.TypeString(block.type))
    print '  is_last: %d' % block.is_last
    print '  length: %d' % block.length
    cur_block += 1
    
    if block.type == metadata.STREAMINFO:
        # print STREAMINFO fields
        streaminfo = block.data.stream_info
        print '  minimum blocksize: %d' % streaminfo.min_blocksize
        print '  maximum blocksize: %d' % streaminfo.max_blocksize
        print '  minimum framesize: %d' % streaminfo.min_framesize
        print '  maximum framesize: %d' % streaminfo.max_framesize
        print '  sample_rate: %d' % streaminfo.sample_rate
        print '  channels: %d' % streaminfo.channels
        print '  bits-per-sample: %d' % streaminfo.bits_per_sample
        print '  total samples: %d' % streaminfo.total_samples
        #print '  md5sum: %s' % streaminfo.md5sum
        
    elif block.type == metadata.SEEKTABLE:
        # print SEEKTABLE fields
        seektable = block.data.seek_table
        print '  seek points: %d' % seektable.num_points
        for i in range(seektable.num_points):
            pt = seektable.points[i]
            print '    point %d: sample_number=%d, stream_offset=%d, frame_samples=%d' % (i, pt.sample_number, pt.stream_offset, pt.frame_samples)
        
    elif block.type == metadata.CUESHEET:
        # print CUESHEET
        cuesheet = block.data.cue_sheet
        print '  media catalog number: %s' % cuesheet.media_catalog_number
        print '  lead-in: %d' % cuesheet.lead_in
        print '  is CD: %d' % cuesheet.is_cd
        print '  number of tracks: %d' % cuesheet.num_tracks
        for i in range(cuesheet.num_tracks):
            tr = cuesheet.tracks[i]
            print '    track[%d]' % i
            print '      offset: %d' % tr.offset
            print '      number: %d' % ord(tr.number)
            print '      ISRC: %s' % tr.isrc
            if tr.type == 0:
                print '      type: AUDIO'
            else:
                print '      type: NON-AUDIO'
            if tr.pre_emphasis == 1:
                print '      pre-emphasis: true'
            else:
                print '      pre-emphasis: false'
            print '      number of index points: %d' % ord(tr.num_indices)
            for j in range(ord(tr.num_indices)):
                print '        index[%d]' % j
                print '          offset: %d' % tr.indices[j].offset
                print '          number: %d' % ord(tr.indices[j].number)        
        
    elif block.type == metadata.VORBIS_COMMENT:
        # print vorbis tags
        comment = block.data.vorbis_comment
        print '  vendor string: %s' % comment.vendor_string
        print '  comments: %d' % comment.num_comments
        for i in range(comment.num_comments):
            print '    comment[%d]: %s' % (i, comment.comments[i])
            
    if not it.next():
        break
