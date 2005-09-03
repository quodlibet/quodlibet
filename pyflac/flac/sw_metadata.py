# This file was created automatically by SWIG.
# Don't modify this file, modify the SWIG interface instead.
# This file is compatible with both classic and new-style classes.

import _sw_metadata

def _swig_setattr_nondynamic(self,class_type,name,value,static=1):
    if (name == "this"):
        if isinstance(value, class_type):
            self.__dict__[name] = value.this
            if hasattr(value,"thisown"): self.__dict__["thisown"] = value.thisown
            del value.thisown
            return
    method = class_type.__swig_setmethods__.get(name,None)
    if method: return method(self,value)
    if (not static) or hasattr(self,name) or (name == "thisown"):
        self.__dict__[name] = value
    else:
        raise AttributeError("You cannot add attributes to %s" % self)

def _swig_setattr(self,class_type,name,value):
    return _swig_setattr_nondynamic(self,class_type,name,value,0)

def _swig_getattr(self,class_type,name):
    method = class_type.__swig_getmethods__.get(name,None)
    if method: return method(self)
    raise AttributeError,name

import types
try:
    _object = types.ObjectType
    _newclass = 1
except AttributeError:
    class _object : pass
    _newclass = 0
del types



TypeString = _sw_metadata.TypeString
FLAC__FILE_DECODER_OK = _sw_metadata.FLAC__FILE_DECODER_OK
FLAC__FILE_DECODER_END_OF_FILE = _sw_metadata.FLAC__FILE_DECODER_END_OF_FILE
FLAC__FILE_DECODER_ERROR_OPENING_FILE = _sw_metadata.FLAC__FILE_DECODER_ERROR_OPENING_FILE
FLAC__FILE_DECODER_MEMORY_ALLOCATION_ERROR = _sw_metadata.FLAC__FILE_DECODER_MEMORY_ALLOCATION_ERROR
FLAC__FILE_DECODER_SEEK_ERROR = _sw_metadata.FLAC__FILE_DECODER_SEEK_ERROR
FLAC__FILE_DECODER_SEEKABLE_STREAM_DECODER_ERROR = _sw_metadata.FLAC__FILE_DECODER_SEEKABLE_STREAM_DECODER_ERROR
FLAC__FILE_DECODER_ALREADY_INITIALIZED = _sw_metadata.FLAC__FILE_DECODER_ALREADY_INITIALIZED
FLAC__FILE_DECODER_INVALID_CALLBACK = _sw_metadata.FLAC__FILE_DECODER_INVALID_CALLBACK
FLAC__FILE_DECODER_UNINITIALIZED = _sw_metadata.FLAC__FILE_DECODER_UNINITIALIZED
class FileDecoder(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FileDecoder, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FileDecoder, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__FileDecoder instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["protected_"] = _sw_metadata.FileDecoder_protected__set
    __swig_getmethods__["protected_"] = _sw_metadata.FileDecoder_protected__get
    if _newclass:protected_ = property(_sw_metadata.FileDecoder_protected__get, _sw_metadata.FileDecoder_protected__set)
    __swig_setmethods__["private_"] = _sw_metadata.FileDecoder_private__set
    __swig_getmethods__["private_"] = _sw_metadata.FileDecoder_private__get
    if _newclass:private_ = property(_sw_metadata.FileDecoder_private__get, _sw_metadata.FileDecoder_private__set)
    def __init__(self, *args):
        _swig_setattr(self, FileDecoder, 'this', _sw_metadata.new_FileDecoder(*args))
        _swig_setattr(self, FileDecoder, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_FileDecoder):
        try:
            if self.thisown: destroy(self)
        except: pass


class FileDecoderPtr(FileDecoder):
    def __init__(self, this):
        _swig_setattr(self, FileDecoder, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FileDecoder, 'thisown', 0)
        _swig_setattr(self, FileDecoder,self.__class__,FileDecoder)
_sw_metadata.FileDecoder_swigregister(FileDecoderPtr)

FLAC__FILE_ENCODER_OK = _sw_metadata.FLAC__FILE_ENCODER_OK
FLAC__FILE_ENCODER_NO_FILENAME = _sw_metadata.FLAC__FILE_ENCODER_NO_FILENAME
FLAC__FILE_ENCODER_SEEKABLE_STREAM_ENCODER_ERROR = _sw_metadata.FLAC__FILE_ENCODER_SEEKABLE_STREAM_ENCODER_ERROR
FLAC__FILE_ENCODER_FATAL_ERROR_WHILE_WRITING = _sw_metadata.FLAC__FILE_ENCODER_FATAL_ERROR_WHILE_WRITING
FLAC__FILE_ENCODER_ERROR_OPENING_FILE = _sw_metadata.FLAC__FILE_ENCODER_ERROR_OPENING_FILE
FLAC__FILE_ENCODER_MEMORY_ALLOCATION_ERROR = _sw_metadata.FLAC__FILE_ENCODER_MEMORY_ALLOCATION_ERROR
FLAC__FILE_ENCODER_ALREADY_INITIALIZED = _sw_metadata.FLAC__FILE_ENCODER_ALREADY_INITIALIZED
FLAC__FILE_ENCODER_UNINITIALIZED = _sw_metadata.FLAC__FILE_ENCODER_UNINITIALIZED
class FileEncoder(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FileEncoder, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FileEncoder, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__FileEncoder instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["protected_"] = _sw_metadata.FileEncoder_protected__set
    __swig_getmethods__["protected_"] = _sw_metadata.FileEncoder_protected__get
    if _newclass:protected_ = property(_sw_metadata.FileEncoder_protected__get, _sw_metadata.FileEncoder_protected__set)
    __swig_setmethods__["private_"] = _sw_metadata.FileEncoder_private__set
    __swig_getmethods__["private_"] = _sw_metadata.FileEncoder_private__get
    if _newclass:private_ = property(_sw_metadata.FileEncoder_private__get, _sw_metadata.FileEncoder_private__set)
    def __init__(self, *args):
        _swig_setattr(self, FileEncoder, 'this', _sw_metadata.new_FileEncoder(*args))
        _swig_setattr(self, FileEncoder, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_FileEncoder):
        try:
            if self.thisown: destroy(self)
        except: pass


class FileEncoderPtr(FileEncoder):
    def __init__(self, this):
        _swig_setattr(self, FileEncoder, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FileEncoder, 'thisown', 0)
        _swig_setattr(self, FileEncoder,self.__class__,FileEncoder)
_sw_metadata.FileEncoder_swigregister(FileEncoderPtr)

class Metadata(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Metadata, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Metadata, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["type"] = _sw_metadata.Metadata_type_set
    __swig_getmethods__["type"] = _sw_metadata.Metadata_type_get
    if _newclass:type = property(_sw_metadata.Metadata_type_get, _sw_metadata.Metadata_type_set)
    __swig_setmethods__["is_last"] = _sw_metadata.Metadata_is_last_set
    __swig_getmethods__["is_last"] = _sw_metadata.Metadata_is_last_get
    if _newclass:is_last = property(_sw_metadata.Metadata_is_last_get, _sw_metadata.Metadata_is_last_set)
    __swig_setmethods__["length"] = _sw_metadata.Metadata_length_set
    __swig_getmethods__["length"] = _sw_metadata.Metadata_length_get
    if _newclass:length = property(_sw_metadata.Metadata_length_get, _sw_metadata.Metadata_length_set)
    __swig_getmethods__["data"] = _sw_metadata.Metadata_data_get
    if _newclass:data = property(_sw_metadata.Metadata_data_get)
    def __init__(self, *args):
        _swig_setattr(self, Metadata, 'this', _sw_metadata.new_Metadata(*args))
        _swig_setattr(self, Metadata, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Metadata):
        try:
            if self.thisown: destroy(self)
        except: pass

    def clone(*args): return _sw_metadata.Metadata_clone(*args)
    def is_equal(*args): return _sw_metadata.Metadata_is_equal(*args)
    def application_set_data(*args): return _sw_metadata.Metadata_application_set_data(*args)
    def seektable_resize_points(*args): return _sw_metadata.Metadata_seektable_resize_points(*args)
    def seektable_set_point(*args): return _sw_metadata.Metadata_seektable_set_point(*args)
    def seektable_insert_point(*args): return _sw_metadata.Metadata_seektable_insert_point(*args)
    def seektable_delete_point(*args): return _sw_metadata.Metadata_seektable_delete_point(*args)
    def seektable_is_legal(*args): return _sw_metadata.Metadata_seektable_is_legal(*args)
    def seektable_template_append_placeholders(*args): return _sw_metadata.Metadata_seektable_template_append_placeholders(*args)
    def seektable_template_append_point(*args): return _sw_metadata.Metadata_seektable_template_append_point(*args)
    def seektable_template_append_points(*args): return _sw_metadata.Metadata_seektable_template_append_points(*args)
    def seektable_template_append_spaced_points(*args): return _sw_metadata.Metadata_seektable_template_append_spaced_points(*args)
    def seektable_template_sort(*args): return _sw_metadata.Metadata_seektable_template_sort(*args)
    def vorbiscomment_set_vendor_string(*args): return _sw_metadata.Metadata_vorbiscomment_set_vendor_string(*args)
    def vorbiscomment_resize_comments(*args): return _sw_metadata.Metadata_vorbiscomment_resize_comments(*args)
    def vorbiscomment_set_comment(*args): return _sw_metadata.Metadata_vorbiscomment_set_comment(*args)
    def vorbiscomment_insert_comment(*args): return _sw_metadata.Metadata_vorbiscomment_insert_comment(*args)
    def vorbiscomment_delete_comment(*args): return _sw_metadata.Metadata_vorbiscomment_delete_comment(*args)
    def vorbiscomment_find_entry_from(*args): return _sw_metadata.Metadata_vorbiscomment_find_entry_from(*args)
    def vorbiscomment_remove_entry_matching(*args): return _sw_metadata.Metadata_vorbiscomment_remove_entry_matching(*args)
    def vorbiscomment_remove_entries_matching(*args): return _sw_metadata.Metadata_vorbiscomment_remove_entries_matching(*args)
    def cuesheet_track_resize_indices(*args): return _sw_metadata.Metadata_cuesheet_track_resize_indices(*args)
    def cuesheet_track_insert_index(*args): return _sw_metadata.Metadata_cuesheet_track_insert_index(*args)
    def cuesheet_track_insert_blank_index(*args): return _sw_metadata.Metadata_cuesheet_track_insert_blank_index(*args)
    def cuesheet_track_delete_index(*args): return _sw_metadata.Metadata_cuesheet_track_delete_index(*args)
    def cuesheet_resize_tracks(*args): return _sw_metadata.Metadata_cuesheet_resize_tracks(*args)
    def cuesheet_insert_track(*args): return _sw_metadata.Metadata_cuesheet_insert_track(*args)
    def cuesheet_insert_blank_track(*args): return _sw_metadata.Metadata_cuesheet_insert_blank_track(*args)
    def cuesheet_delete_track(*args): return _sw_metadata.Metadata_cuesheet_delete_track(*args)
    def cuesheet_is_legal(*args): return _sw_metadata.Metadata_cuesheet_is_legal(*args)

class MetadataPtr(Metadata):
    def __init__(self, this):
        _swig_setattr(self, Metadata, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Metadata, 'thisown', 0)
        _swig_setattr(self, Metadata,self.__class__,Metadata)
_sw_metadata.Metadata_swigregister(MetadataPtr)

class FLAC__StreamMetadata_data(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FLAC__StreamMetadata_data, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FLAC__StreamMetadata_data, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_data instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["stream_info"] = _sw_metadata.FLAC__StreamMetadata_data_stream_info_set
    __swig_getmethods__["stream_info"] = _sw_metadata.FLAC__StreamMetadata_data_stream_info_get
    if _newclass:stream_info = property(_sw_metadata.FLAC__StreamMetadata_data_stream_info_get, _sw_metadata.FLAC__StreamMetadata_data_stream_info_set)
    __swig_setmethods__["padding"] = _sw_metadata.FLAC__StreamMetadata_data_padding_set
    __swig_getmethods__["padding"] = _sw_metadata.FLAC__StreamMetadata_data_padding_get
    if _newclass:padding = property(_sw_metadata.FLAC__StreamMetadata_data_padding_get, _sw_metadata.FLAC__StreamMetadata_data_padding_set)
    __swig_setmethods__["application"] = _sw_metadata.FLAC__StreamMetadata_data_application_set
    __swig_getmethods__["application"] = _sw_metadata.FLAC__StreamMetadata_data_application_get
    if _newclass:application = property(_sw_metadata.FLAC__StreamMetadata_data_application_get, _sw_metadata.FLAC__StreamMetadata_data_application_set)
    __swig_setmethods__["seek_table"] = _sw_metadata.FLAC__StreamMetadata_data_seek_table_set
    __swig_getmethods__["seek_table"] = _sw_metadata.FLAC__StreamMetadata_data_seek_table_get
    if _newclass:seek_table = property(_sw_metadata.FLAC__StreamMetadata_data_seek_table_get, _sw_metadata.FLAC__StreamMetadata_data_seek_table_set)
    __swig_setmethods__["vorbis_comment"] = _sw_metadata.FLAC__StreamMetadata_data_vorbis_comment_set
    __swig_getmethods__["vorbis_comment"] = _sw_metadata.FLAC__StreamMetadata_data_vorbis_comment_get
    if _newclass:vorbis_comment = property(_sw_metadata.FLAC__StreamMetadata_data_vorbis_comment_get, _sw_metadata.FLAC__StreamMetadata_data_vorbis_comment_set)
    __swig_setmethods__["cue_sheet"] = _sw_metadata.FLAC__StreamMetadata_data_cue_sheet_set
    __swig_getmethods__["cue_sheet"] = _sw_metadata.FLAC__StreamMetadata_data_cue_sheet_get
    if _newclass:cue_sheet = property(_sw_metadata.FLAC__StreamMetadata_data_cue_sheet_get, _sw_metadata.FLAC__StreamMetadata_data_cue_sheet_set)
    __swig_setmethods__["unknown"] = _sw_metadata.FLAC__StreamMetadata_data_unknown_set
    __swig_getmethods__["unknown"] = _sw_metadata.FLAC__StreamMetadata_data_unknown_get
    if _newclass:unknown = property(_sw_metadata.FLAC__StreamMetadata_data_unknown_get, _sw_metadata.FLAC__StreamMetadata_data_unknown_set)
    def __init__(self, *args):
        _swig_setattr(self, FLAC__StreamMetadata_data, 'this', _sw_metadata.new_FLAC__StreamMetadata_data(*args))
        _swig_setattr(self, FLAC__StreamMetadata_data, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_FLAC__StreamMetadata_data):
        try:
            if self.thisown: destroy(self)
        except: pass


class FLAC__StreamMetadata_dataPtr(FLAC__StreamMetadata_data):
    def __init__(self, this):
        _swig_setattr(self, FLAC__StreamMetadata_data, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FLAC__StreamMetadata_data, 'thisown', 0)
        _swig_setattr(self, FLAC__StreamMetadata_data,self.__class__,FLAC__StreamMetadata_data)
_sw_metadata.FLAC__StreamMetadata_data_swigregister(FLAC__StreamMetadata_dataPtr)

class StreamInfo(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, StreamInfo, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, StreamInfo, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_StreamInfo instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["min_blocksize"] = _sw_metadata.StreamInfo_min_blocksize_set
    __swig_getmethods__["min_blocksize"] = _sw_metadata.StreamInfo_min_blocksize_get
    if _newclass:min_blocksize = property(_sw_metadata.StreamInfo_min_blocksize_get, _sw_metadata.StreamInfo_min_blocksize_set)
    __swig_setmethods__["max_blocksize"] = _sw_metadata.StreamInfo_max_blocksize_set
    __swig_getmethods__["max_blocksize"] = _sw_metadata.StreamInfo_max_blocksize_get
    if _newclass:max_blocksize = property(_sw_metadata.StreamInfo_max_blocksize_get, _sw_metadata.StreamInfo_max_blocksize_set)
    __swig_setmethods__["min_framesize"] = _sw_metadata.StreamInfo_min_framesize_set
    __swig_getmethods__["min_framesize"] = _sw_metadata.StreamInfo_min_framesize_get
    if _newclass:min_framesize = property(_sw_metadata.StreamInfo_min_framesize_get, _sw_metadata.StreamInfo_min_framesize_set)
    __swig_setmethods__["max_framesize"] = _sw_metadata.StreamInfo_max_framesize_set
    __swig_getmethods__["max_framesize"] = _sw_metadata.StreamInfo_max_framesize_get
    if _newclass:max_framesize = property(_sw_metadata.StreamInfo_max_framesize_get, _sw_metadata.StreamInfo_max_framesize_set)
    __swig_setmethods__["sample_rate"] = _sw_metadata.StreamInfo_sample_rate_set
    __swig_getmethods__["sample_rate"] = _sw_metadata.StreamInfo_sample_rate_get
    if _newclass:sample_rate = property(_sw_metadata.StreamInfo_sample_rate_get, _sw_metadata.StreamInfo_sample_rate_set)
    __swig_setmethods__["channels"] = _sw_metadata.StreamInfo_channels_set
    __swig_getmethods__["channels"] = _sw_metadata.StreamInfo_channels_get
    if _newclass:channels = property(_sw_metadata.StreamInfo_channels_get, _sw_metadata.StreamInfo_channels_set)
    __swig_setmethods__["bits_per_sample"] = _sw_metadata.StreamInfo_bits_per_sample_set
    __swig_getmethods__["bits_per_sample"] = _sw_metadata.StreamInfo_bits_per_sample_get
    if _newclass:bits_per_sample = property(_sw_metadata.StreamInfo_bits_per_sample_get, _sw_metadata.StreamInfo_bits_per_sample_set)
    __swig_setmethods__["total_samples"] = _sw_metadata.StreamInfo_total_samples_set
    __swig_getmethods__["total_samples"] = _sw_metadata.StreamInfo_total_samples_get
    if _newclass:total_samples = property(_sw_metadata.StreamInfo_total_samples_get, _sw_metadata.StreamInfo_total_samples_set)
    __swig_setmethods__["md5sum"] = _sw_metadata.StreamInfo_md5sum_set
    __swig_getmethods__["md5sum"] = _sw_metadata.StreamInfo_md5sum_get
    if _newclass:md5sum = property(_sw_metadata.StreamInfo_md5sum_get, _sw_metadata.StreamInfo_md5sum_set)
    def __init__(self, *args):
        _swig_setattr(self, StreamInfo, 'this', _sw_metadata.new_StreamInfo(*args))
        _swig_setattr(self, StreamInfo, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_StreamInfo):
        try:
            if self.thisown: destroy(self)
        except: pass


class StreamInfoPtr(StreamInfo):
    def __init__(self, this):
        _swig_setattr(self, StreamInfo, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, StreamInfo, 'thisown', 0)
        _swig_setattr(self, StreamInfo,self.__class__,StreamInfo)
_sw_metadata.StreamInfo_swigregister(StreamInfoPtr)

class Padding(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Padding, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Padding, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Padding instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["dummy"] = _sw_metadata.Padding_dummy_set
    __swig_getmethods__["dummy"] = _sw_metadata.Padding_dummy_get
    if _newclass:dummy = property(_sw_metadata.Padding_dummy_get, _sw_metadata.Padding_dummy_set)
    def __init__(self, *args):
        _swig_setattr(self, Padding, 'this', _sw_metadata.new_Padding(*args))
        _swig_setattr(self, Padding, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Padding):
        try:
            if self.thisown: destroy(self)
        except: pass


class PaddingPtr(Padding):
    def __init__(self, this):
        _swig_setattr(self, Padding, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Padding, 'thisown', 0)
        _swig_setattr(self, Padding,self.__class__,Padding)
_sw_metadata.Padding_swigregister(PaddingPtr)

class Application(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Application, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Application, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Application instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["id"] = _sw_metadata.Application_id_set
    __swig_getmethods__["id"] = _sw_metadata.Application_id_get
    if _newclass:id = property(_sw_metadata.Application_id_get, _sw_metadata.Application_id_set)
    __swig_setmethods__["data"] = _sw_metadata.Application_data_set
    __swig_getmethods__["data"] = _sw_metadata.Application_data_get
    if _newclass:data = property(_sw_metadata.Application_data_get, _sw_metadata.Application_data_set)
    def __init__(self, *args):
        _swig_setattr(self, Application, 'this', _sw_metadata.new_Application(*args))
        _swig_setattr(self, Application, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Application):
        try:
            if self.thisown: destroy(self)
        except: pass


class ApplicationPtr(Application):
    def __init__(self, this):
        _swig_setattr(self, Application, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Application, 'thisown', 0)
        _swig_setattr(self, Application,self.__class__,Application)
_sw_metadata.Application_swigregister(ApplicationPtr)

class SeekPoint(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SeekPoint, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SeekPoint, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_SeekPoint instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["sample_number"] = _sw_metadata.SeekPoint_sample_number_set
    __swig_getmethods__["sample_number"] = _sw_metadata.SeekPoint_sample_number_get
    if _newclass:sample_number = property(_sw_metadata.SeekPoint_sample_number_get, _sw_metadata.SeekPoint_sample_number_set)
    __swig_setmethods__["stream_offset"] = _sw_metadata.SeekPoint_stream_offset_set
    __swig_getmethods__["stream_offset"] = _sw_metadata.SeekPoint_stream_offset_get
    if _newclass:stream_offset = property(_sw_metadata.SeekPoint_stream_offset_get, _sw_metadata.SeekPoint_stream_offset_set)
    __swig_setmethods__["frame_samples"] = _sw_metadata.SeekPoint_frame_samples_set
    __swig_getmethods__["frame_samples"] = _sw_metadata.SeekPoint_frame_samples_get
    if _newclass:frame_samples = property(_sw_metadata.SeekPoint_frame_samples_get, _sw_metadata.SeekPoint_frame_samples_set)
    def __getitem__(*args): return _sw_metadata.SeekPoint___getitem__(*args)
    def __init__(self, *args):
        _swig_setattr(self, SeekPoint, 'this', _sw_metadata.new_SeekPoint(*args))
        _swig_setattr(self, SeekPoint, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_SeekPoint):
        try:
            if self.thisown: destroy(self)
        except: pass


class SeekPointPtr(SeekPoint):
    def __init__(self, this):
        _swig_setattr(self, SeekPoint, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, SeekPoint, 'thisown', 0)
        _swig_setattr(self, SeekPoint,self.__class__,SeekPoint)
_sw_metadata.SeekPoint_swigregister(SeekPointPtr)

class SeekTable(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SeekTable, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SeekTable, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_SeekTable instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["num_points"] = _sw_metadata.SeekTable_num_points_set
    __swig_getmethods__["num_points"] = _sw_metadata.SeekTable_num_points_get
    if _newclass:num_points = property(_sw_metadata.SeekTable_num_points_get, _sw_metadata.SeekTable_num_points_set)
    __swig_setmethods__["points"] = _sw_metadata.SeekTable_points_set
    __swig_getmethods__["points"] = _sw_metadata.SeekTable_points_get
    if _newclass:points = property(_sw_metadata.SeekTable_points_get, _sw_metadata.SeekTable_points_set)
    def __init__(self, *args):
        _swig_setattr(self, SeekTable, 'this', _sw_metadata.new_SeekTable(*args))
        _swig_setattr(self, SeekTable, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_SeekTable):
        try:
            if self.thisown: destroy(self)
        except: pass


class SeekTablePtr(SeekTable):
    def __init__(self, this):
        _swig_setattr(self, SeekTable, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, SeekTable, 'thisown', 0)
        _swig_setattr(self, SeekTable,self.__class__,SeekTable)
_sw_metadata.SeekTable_swigregister(SeekTablePtr)

class VorbisCommentEntry(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, VorbisCommentEntry, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, VorbisCommentEntry, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_VorbisComment_Entry instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["length"] = _sw_metadata.VorbisCommentEntry_length_set
    __swig_getmethods__["length"] = _sw_metadata.VorbisCommentEntry_length_get
    if _newclass:length = property(_sw_metadata.VorbisCommentEntry_length_get, _sw_metadata.VorbisCommentEntry_length_set)
    __swig_setmethods__["entry"] = _sw_metadata.VorbisCommentEntry_entry_set
    __swig_getmethods__["entry"] = _sw_metadata.VorbisCommentEntry_entry_get
    if _newclass:entry = property(_sw_metadata.VorbisCommentEntry_entry_get, _sw_metadata.VorbisCommentEntry_entry_set)
    def matches(*args): return _sw_metadata.VorbisCommentEntry_matches(*args)
    def __getitem__(*args): return _sw_metadata.VorbisCommentEntry___getitem__(*args)
    def __init__(self, *args):
        _swig_setattr(self, VorbisCommentEntry, 'this', _sw_metadata.new_VorbisCommentEntry(*args))
        _swig_setattr(self, VorbisCommentEntry, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_VorbisCommentEntry):
        try:
            if self.thisown: destroy(self)
        except: pass


class VorbisCommentEntryPtr(VorbisCommentEntry):
    def __init__(self, this):
        _swig_setattr(self, VorbisCommentEntry, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, VorbisCommentEntry, 'thisown', 0)
        _swig_setattr(self, VorbisCommentEntry,self.__class__,VorbisCommentEntry)
_sw_metadata.VorbisCommentEntry_swigregister(VorbisCommentEntryPtr)

class VorbisComment(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, VorbisComment, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, VorbisComment, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_VorbisComment instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["vendor_string"] = _sw_metadata.VorbisComment_vendor_string_set
    __swig_getmethods__["vendor_string"] = _sw_metadata.VorbisComment_vendor_string_get
    if _newclass:vendor_string = property(_sw_metadata.VorbisComment_vendor_string_get, _sw_metadata.VorbisComment_vendor_string_set)
    __swig_setmethods__["num_comments"] = _sw_metadata.VorbisComment_num_comments_set
    __swig_getmethods__["num_comments"] = _sw_metadata.VorbisComment_num_comments_get
    if _newclass:num_comments = property(_sw_metadata.VorbisComment_num_comments_get, _sw_metadata.VorbisComment_num_comments_set)
    __swig_setmethods__["comments"] = _sw_metadata.VorbisComment_comments_set
    __swig_getmethods__["comments"] = _sw_metadata.VorbisComment_comments_get
    if _newclass:comments = property(_sw_metadata.VorbisComment_comments_get, _sw_metadata.VorbisComment_comments_set)
    def __init__(self, *args):
        _swig_setattr(self, VorbisComment, 'this', _sw_metadata.new_VorbisComment(*args))
        _swig_setattr(self, VorbisComment, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_VorbisComment):
        try:
            if self.thisown: destroy(self)
        except: pass


class VorbisCommentPtr(VorbisComment):
    def __init__(self, this):
        _swig_setattr(self, VorbisComment, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, VorbisComment, 'thisown', 0)
        _swig_setattr(self, VorbisComment,self.__class__,VorbisComment)
_sw_metadata.VorbisComment_swigregister(VorbisCommentPtr)

class CueSheetIndex(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheetIndex, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheetIndex, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet_Index instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["offset"] = _sw_metadata.CueSheetIndex_offset_set
    __swig_getmethods__["offset"] = _sw_metadata.CueSheetIndex_offset_get
    if _newclass:offset = property(_sw_metadata.CueSheetIndex_offset_get, _sw_metadata.CueSheetIndex_offset_set)
    __swig_setmethods__["number"] = _sw_metadata.CueSheetIndex_number_set
    __swig_getmethods__["number"] = _sw_metadata.CueSheetIndex_number_get
    if _newclass:number = property(_sw_metadata.CueSheetIndex_number_get, _sw_metadata.CueSheetIndex_number_set)
    def __getitem__(*args): return _sw_metadata.CueSheetIndex___getitem__(*args)
    def __init__(self, *args):
        _swig_setattr(self, CueSheetIndex, 'this', _sw_metadata.new_CueSheetIndex(*args))
        _swig_setattr(self, CueSheetIndex, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_CueSheetIndex):
        try:
            if self.thisown: destroy(self)
        except: pass


class CueSheetIndexPtr(CueSheetIndex):
    def __init__(self, this):
        _swig_setattr(self, CueSheetIndex, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheetIndex, 'thisown', 0)
        _swig_setattr(self, CueSheetIndex,self.__class__,CueSheetIndex)
_sw_metadata.CueSheetIndex_swigregister(CueSheetIndexPtr)

class CueSheetTrack(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheetTrack, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheetTrack, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet_Track instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["offset"] = _sw_metadata.CueSheetTrack_offset_set
    __swig_getmethods__["offset"] = _sw_metadata.CueSheetTrack_offset_get
    if _newclass:offset = property(_sw_metadata.CueSheetTrack_offset_get, _sw_metadata.CueSheetTrack_offset_set)
    __swig_setmethods__["number"] = _sw_metadata.CueSheetTrack_number_set
    __swig_getmethods__["number"] = _sw_metadata.CueSheetTrack_number_get
    if _newclass:number = property(_sw_metadata.CueSheetTrack_number_get, _sw_metadata.CueSheetTrack_number_set)
    __swig_setmethods__["isrc"] = _sw_metadata.CueSheetTrack_isrc_set
    __swig_getmethods__["isrc"] = _sw_metadata.CueSheetTrack_isrc_get
    if _newclass:isrc = property(_sw_metadata.CueSheetTrack_isrc_get, _sw_metadata.CueSheetTrack_isrc_set)
    __swig_setmethods__["type"] = _sw_metadata.CueSheetTrack_type_set
    __swig_getmethods__["type"] = _sw_metadata.CueSheetTrack_type_get
    if _newclass:type = property(_sw_metadata.CueSheetTrack_type_get, _sw_metadata.CueSheetTrack_type_set)
    __swig_setmethods__["pre_emphasis"] = _sw_metadata.CueSheetTrack_pre_emphasis_set
    __swig_getmethods__["pre_emphasis"] = _sw_metadata.CueSheetTrack_pre_emphasis_get
    if _newclass:pre_emphasis = property(_sw_metadata.CueSheetTrack_pre_emphasis_get, _sw_metadata.CueSheetTrack_pre_emphasis_set)
    __swig_setmethods__["num_indices"] = _sw_metadata.CueSheetTrack_num_indices_set
    __swig_getmethods__["num_indices"] = _sw_metadata.CueSheetTrack_num_indices_get
    if _newclass:num_indices = property(_sw_metadata.CueSheetTrack_num_indices_get, _sw_metadata.CueSheetTrack_num_indices_set)
    __swig_setmethods__["indices"] = _sw_metadata.CueSheetTrack_indices_set
    __swig_getmethods__["indices"] = _sw_metadata.CueSheetTrack_indices_get
    if _newclass:indices = property(_sw_metadata.CueSheetTrack_indices_get, _sw_metadata.CueSheetTrack_indices_set)
    def __init__(self, *args):
        _swig_setattr(self, CueSheetTrack, 'this', _sw_metadata.new_CueSheetTrack(*args))
        _swig_setattr(self, CueSheetTrack, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_CueSheetTrack):
        try:
            if self.thisown: destroy(self)
        except: pass

    def clone(*args): return _sw_metadata.CueSheetTrack_clone(*args)
    def __getitem__(*args): return _sw_metadata.CueSheetTrack___getitem__(*args)

class CueSheetTrackPtr(CueSheetTrack):
    def __init__(self, this):
        _swig_setattr(self, CueSheetTrack, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheetTrack, 'thisown', 0)
        _swig_setattr(self, CueSheetTrack,self.__class__,CueSheetTrack)
_sw_metadata.CueSheetTrack_swigregister(CueSheetTrackPtr)

class CueSheet(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheet, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheet, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["media_catalog_number"] = _sw_metadata.CueSheet_media_catalog_number_set
    __swig_getmethods__["media_catalog_number"] = _sw_metadata.CueSheet_media_catalog_number_get
    if _newclass:media_catalog_number = property(_sw_metadata.CueSheet_media_catalog_number_get, _sw_metadata.CueSheet_media_catalog_number_set)
    __swig_setmethods__["lead_in"] = _sw_metadata.CueSheet_lead_in_set
    __swig_getmethods__["lead_in"] = _sw_metadata.CueSheet_lead_in_get
    if _newclass:lead_in = property(_sw_metadata.CueSheet_lead_in_get, _sw_metadata.CueSheet_lead_in_set)
    __swig_setmethods__["is_cd"] = _sw_metadata.CueSheet_is_cd_set
    __swig_getmethods__["is_cd"] = _sw_metadata.CueSheet_is_cd_get
    if _newclass:is_cd = property(_sw_metadata.CueSheet_is_cd_get, _sw_metadata.CueSheet_is_cd_set)
    __swig_setmethods__["num_tracks"] = _sw_metadata.CueSheet_num_tracks_set
    __swig_getmethods__["num_tracks"] = _sw_metadata.CueSheet_num_tracks_get
    if _newclass:num_tracks = property(_sw_metadata.CueSheet_num_tracks_get, _sw_metadata.CueSheet_num_tracks_set)
    __swig_setmethods__["tracks"] = _sw_metadata.CueSheet_tracks_set
    __swig_getmethods__["tracks"] = _sw_metadata.CueSheet_tracks_get
    if _newclass:tracks = property(_sw_metadata.CueSheet_tracks_get, _sw_metadata.CueSheet_tracks_set)
    def __init__(self, *args):
        _swig_setattr(self, CueSheet, 'this', _sw_metadata.new_CueSheet(*args))
        _swig_setattr(self, CueSheet, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_CueSheet):
        try:
            if self.thisown: destroy(self)
        except: pass


class CueSheetPtr(CueSheet):
    def __init__(self, this):
        _swig_setattr(self, CueSheet, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheet, 'thisown', 0)
        _swig_setattr(self, CueSheet,self.__class__,CueSheet)
_sw_metadata.CueSheet_swigregister(CueSheetPtr)

class Unknown(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Unknown, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Unknown, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Unknown instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["data"] = _sw_metadata.Unknown_data_set
    __swig_getmethods__["data"] = _sw_metadata.Unknown_data_get
    if _newclass:data = property(_sw_metadata.Unknown_data_get, _sw_metadata.Unknown_data_set)
    def __init__(self, *args):
        _swig_setattr(self, Unknown, 'this', _sw_metadata.new_Unknown(*args))
        _swig_setattr(self, Unknown, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Unknown):
        try:
            if self.thisown: destroy(self)
        except: pass


class UnknownPtr(Unknown):
    def __init__(self, this):
        _swig_setattr(self, Unknown, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Unknown, 'thisown', 0)
        _swig_setattr(self, Unknown,self.__class__,Unknown)
_sw_metadata.Unknown_swigregister(UnknownPtr)

STREAMINFO = _sw_metadata.STREAMINFO
PADDING = _sw_metadata.PADDING
APPLICATION = _sw_metadata.APPLICATION
SEEKTABLE = _sw_metadata.SEEKTABLE
VORBIS_COMMENT = _sw_metadata.VORBIS_COMMENT
CUESHEET = _sw_metadata.CUESHEET
UNDEFINED = _sw_metadata.UNDEFINED
FLAC__METADATA_CHAIN_STATUS_OK = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_OK
FLAC__METADATA_CHAIN_STATUS_ILLEGAL_INPUT = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_ILLEGAL_INPUT
FLAC__METADATA_CHAIN_STATUS_ERROR_OPENING_FILE = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_ERROR_OPENING_FILE
FLAC__METADATA_CHAIN_STATUS_NOT_A_FLAC_FILE = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_NOT_A_FLAC_FILE
FLAC__METADATA_CHAIN_STATUS_NOT_WRITABLE = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_NOT_WRITABLE
FLAC__METADATA_CHAIN_STATUS_BAD_METADATA = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_BAD_METADATA
FLAC__METADATA_CHAIN_STATUS_READ_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_READ_ERROR
FLAC__METADATA_CHAIN_STATUS_SEEK_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_SEEK_ERROR
FLAC__METADATA_CHAIN_STATUS_WRITE_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_WRITE_ERROR
FLAC__METADATA_CHAIN_STATUS_RENAME_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_RENAME_ERROR
FLAC__METADATA_CHAIN_STATUS_UNLINK_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_UNLINK_ERROR
FLAC__METADATA_CHAIN_STATUS_MEMORY_ALLOCATION_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_MEMORY_ALLOCATION_ERROR
FLAC__METADATA_CHAIN_STATUS_INTERNAL_ERROR = _sw_metadata.FLAC__METADATA_CHAIN_STATUS_INTERNAL_ERROR
class Chain(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Chain, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Chain, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__Metadata_Chain instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    def __init__(self, *args):
        _swig_setattr(self, Chain, 'this', _sw_metadata.new_Chain(*args))
        _swig_setattr(self, Chain, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Chain):
        try:
            if self.thisown: destroy(self)
        except: pass

    def status(*args): return _sw_metadata.Chain_status(*args)
    def read(*args): return _sw_metadata.Chain_read(*args)
    def write(*args): return _sw_metadata.Chain_write(*args)
    def merge_padding(*args): return _sw_metadata.Chain_merge_padding(*args)
    def sort_padding(*args): return _sw_metadata.Chain_sort_padding(*args)

class ChainPtr(Chain):
    def __init__(self, this):
        _swig_setattr(self, Chain, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Chain, 'thisown', 0)
        _swig_setattr(self, Chain,self.__class__,Chain)
_sw_metadata.Chain_swigregister(ChainPtr)

class Iterator(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Iterator, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Iterator, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__Metadata_Iterator instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    def __init__(self, *args):
        _swig_setattr(self, Iterator, 'this', _sw_metadata.new_Iterator(*args))
        _swig_setattr(self, Iterator, 'thisown', 1)
    def __del__(self, destroy=_sw_metadata.delete_Iterator):
        try:
            if self.thisown: destroy(self)
        except: pass

    def init(*args): return _sw_metadata.Iterator_init(*args)
    def next(*args): return _sw_metadata.Iterator_next(*args)
    def prev(*args): return _sw_metadata.Iterator_prev(*args)
    def get_block_type(*args): return _sw_metadata.Iterator_get_block_type(*args)
    def get_block(*args): return _sw_metadata.Iterator_get_block(*args)
    def set_block(*args): return _sw_metadata.Iterator_set_block(*args)
    def delete_block(*args): return _sw_metadata.Iterator_delete_block(*args)
    def insert_block_before(*args): return _sw_metadata.Iterator_insert_block_before(*args)
    def insert_block_after(*args): return _sw_metadata.Iterator_insert_block_after(*args)

class IteratorPtr(Iterator):
    def __init__(self, this):
        _swig_setattr(self, Iterator, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Iterator, 'thisown', 0)
        _swig_setattr(self, Iterator,self.__class__,Iterator)
_sw_metadata.Iterator_swigregister(IteratorPtr)


