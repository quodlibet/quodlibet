# ******************************************************
# Copyright 2004: David Collett
# David Collett <david.collett@dart.net.au>
#
# * This program is free software; you can redistribute it and/or
# * modify it under the terms of the GNU General Public License
# * as published by the Free Software Foundation; either version 2
# * of the License, or (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
# ******************************************************
#!/usr/bin/python

# import everything from metaflac
from sw_metadata import *

# override classes for nicer write access interface
# this is backward compatable with plain metaflac module
# when reading only
class VorbisComment:

    class Comments:
        def __init__(self, block):
            self.block = block
            self.count = -1
        def __setitem__(self, name, value):
            if type(name) == int:
                self.block.vorbiscomment_set_comment(name, value, True)
            elif type(name) == str:
                self.block.vorbiscomment_insert_comment(self.block.data.vorbis_comment.num_comments, "%s=%s" % (name, value), True)
        def __delitem__(self, name):
            if type(name) == str:
                self.block.vorbiscomment_remove_entry_matching(name)
            elif type(name) == int:
                self.block.vorbiscomment_delete_comment(name)
        def __getitem__(self, name):
            if type(name) == int:
                if(name >= 0 and name < self.block.data.vorbis_comment.num_comments):
                    return self.block.data.vorbis_comment.comments[name]
                else:
                    raise IndexError, "Index %d out of range" % name
            elif type(name) == str:
                idx = self.block.vorbiscomment_find_entry_from(0, name)
                if idx != -1:
                    return self.block.data.vorbis_comment.comments[idx].split('=',1)[1]
                else:
                    raise KeyError, name
        def __iter__(self):
            return self
        def next(self):
            if self.count < self.block.data.vorbis_comment.num_comments - 1:
                self.count += 1
                return self.block.data.vorbis_comment.comments[self.count]
            else:
                self.count = -1
                raise StopIteration

    def __init__(self, block=None):
        if block:
            self.block = block
        else:
            self.block = Metadata(VORBIS_COMMENT)
        self.comments = VorbisComment.Comments(self.block)

    def __getattr__(self, name):
        try:
            return self.block.data.vorbis_comment.__getattr__(name)
        except AttributeError:
            return self.block.__getattr__(name)

    def __setattr__(self, name, value):
        # this is the only user-settable attribute...
        if name=='vendor_string':
            self.block.vorbiscomment_set_vendor_string(value, True);
        else:
            self.__dict__[name] = value

class SeekTable:
    def __init__(self, block=None):
        if block:
            self.block = block
        else:
            self.block = Metadata(SEEKTABLE)
#    def template_append_spaced_points(self, num_points, total_samples):
#        return self.block.seektable_template_append_spaced_points(num_points, total_samples)
    def __getattr__(self, name):
        try:
            return eval("self.block.seektable_%s" % name)
        except AttributeError:
            try:
                return self.block.data.seektable.__getattr__(name)
            except AttributeError:
                return self.block.__getattr__(name)
