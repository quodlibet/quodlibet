#!/usr/bin/python
# heres an example of using some python magic to
# easily view and modify vorbis comments

import flac.metadata as metadata
import sys

# create a chain
chain = metadata.Chain()
chain.read(sys.argv[1])

# get iterator, init
it = metadata.Iterator()
it.init(chain)

while 1:
    if it.get_block_type() == metadata.VORBIS_COMMENT:
        block = it.get_block()
        vc = metadata.VorbisComment(block)
        break
    if not it.next():
        break

if vc:
    # print num_comments, vendor string
    print 'num_comments: %d' % vc.num_comments
    print 'vendor string: %s' % vc.vendor_string
    # print an existing comment by field name
    try:
        print vc.comments['TTITLE1']
    except KeyError:
        pass
    
    # print all comments
    for c in vc.comments:
        print c
        
    # change vendor string
    vc.vendor_string = 'Added by pyflac!'

    # insert/modify/delete comments
    # if a tag doesnt already exist, it will be added
    vc.comments['ARTIST'] = 'My Artist'
    del vc.comments['DISCID']
    vc.comments['MYTEST'] = 'blah'

    # print again
    for c in vc.comments:
        print c
    
# write chain back to disk
print chain.write(True,True)
