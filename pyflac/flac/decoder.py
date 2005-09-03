# This file was created automatically by SWIG.
# Don't modify this file, modify the SWIG interface instead.
# This file is compatible with both classic and new-style classes.

import _decoder

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


FLAC__FILE_DECODER_OK = _decoder.FLAC__FILE_DECODER_OK
FLAC__FILE_DECODER_END_OF_FILE = _decoder.FLAC__FILE_DECODER_END_OF_FILE
FLAC__FILE_DECODER_ERROR_OPENING_FILE = _decoder.FLAC__FILE_DECODER_ERROR_OPENING_FILE
FLAC__FILE_DECODER_MEMORY_ALLOCATION_ERROR = _decoder.FLAC__FILE_DECODER_MEMORY_ALLOCATION_ERROR
FLAC__FILE_DECODER_SEEK_ERROR = _decoder.FLAC__FILE_DECODER_SEEK_ERROR
FLAC__FILE_DECODER_SEEKABLE_STREAM_DECODER_ERROR = _decoder.FLAC__FILE_DECODER_SEEKABLE_STREAM_DECODER_ERROR
FLAC__FILE_DECODER_ALREADY_INITIALIZED = _decoder.FLAC__FILE_DECODER_ALREADY_INITIALIZED
FLAC__FILE_DECODER_INVALID_CALLBACK = _decoder.FLAC__FILE_DECODER_INVALID_CALLBACK
FLAC__FILE_DECODER_UNINITIALIZED = _decoder.FLAC__FILE_DECODER_UNINITIALIZED
class FileDecoder(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FileDecoder, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FileDecoder, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__FileDecoder instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["protected_"] = _decoder.FileDecoder_protected__set
    __swig_getmethods__["protected_"] = _decoder.FileDecoder_protected__get
    if _newclass:protected_ = property(_decoder.FileDecoder_protected__get, _decoder.FileDecoder_protected__set)
    __swig_setmethods__["private_"] = _decoder.FileDecoder_private__set
    __swig_getmethods__["private_"] = _decoder.FileDecoder_private__get
    if _newclass:private_ = property(_decoder.FileDecoder_private__get, _decoder.FileDecoder_private__set)
    def __init__(self, *args):
        _swig_setattr(self, FileDecoder, 'this', _decoder.new_FileDecoder(*args))
        _swig_setattr(self, FileDecoder, 'thisown', 1)
    def delete(*args): return _decoder.FileDecoder_delete(*args)
    def set_md5_checking(*args): return _decoder.FileDecoder_set_md5_checking(*args)
    def set_filename(*args): return _decoder.FileDecoder_set_filename(*args)
    def set_write_callback(*args): return _decoder.FileDecoder_set_write_callback(*args)
    def set_error_callback(*args): return _decoder.FileDecoder_set_error_callback(*args)
    def set_metadata_callback(*args): return _decoder.FileDecoder_set_metadata_callback(*args)
    def set_metadata_respond_all(*args): return _decoder.FileDecoder_set_metadata_respond_all(*args)
    def set_metadata_respond(*args): return _decoder.FileDecoder_set_metadata_respond(*args)
    def set_metadata_respond_application(*args): return _decoder.FileDecoder_set_metadata_respond_application(*args)
    def set_metadata_ignore_all(*args): return _decoder.FileDecoder_set_metadata_ignore_all(*args)
    def set_metadata_ignore(*args): return _decoder.FileDecoder_set_metadata_ignore(*args)
    def set_metadata_ignore_application(*args): return _decoder.FileDecoder_set_metadata_ignore_application(*args)
    def get_state(*args): return _decoder.FileDecoder_get_state(*args)
    def get_seekable_stream_decoder_state(*args): return _decoder.FileDecoder_get_seekable_stream_decoder_state(*args)
    def get_stream_decoder_state(*args): return _decoder.FileDecoder_get_stream_decoder_state(*args)
    def get_resolved_state_string(*args): return _decoder.FileDecoder_get_resolved_state_string(*args)
    def get_md5_checking(*args): return _decoder.FileDecoder_get_md5_checking(*args)
    def get_channel_assignment(*args): return _decoder.FileDecoder_get_channel_assignment(*args)
    def get_channels(*args): return _decoder.FileDecoder_get_channels(*args)
    def get_bits_per_sample(*args): return _decoder.FileDecoder_get_bits_per_sample(*args)
    def get_sample_rate(*args): return _decoder.FileDecoder_get_sample_rate(*args)
    def get_blocksize(*args): return _decoder.FileDecoder_get_blocksize(*args)
    def get_decode_position(*args): return _decoder.FileDecoder_get_decode_position(*args)
    def init(*args): return _decoder.FileDecoder_init(*args)
    def finish(*args): return _decoder.FileDecoder_finish(*args)
    def process_single(*args): return _decoder.FileDecoder_process_single(*args)
    def process_until_end_of_metadata(*args): return _decoder.FileDecoder_process_until_end_of_metadata(*args)
    def process_until_end_of_file(*args): return _decoder.FileDecoder_process_until_end_of_file(*args)
    def seek_absolute(*args): return _decoder.FileDecoder_seek_absolute(*args)
    def __del__(self, destroy=_decoder.delete_FileDecoder):
        try:
            if self.thisown: destroy(self)
        except: pass


class FileDecoderPtr(FileDecoder):
    def __init__(self, this):
        _swig_setattr(self, FileDecoder, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FileDecoder, 'thisown', 0)
        _swig_setattr(self, FileDecoder,self.__class__,FileDecoder)
_decoder.FileDecoder_swigregister(FileDecoderPtr)

FLAC__FILE_ENCODER_OK = _decoder.FLAC__FILE_ENCODER_OK
FLAC__FILE_ENCODER_NO_FILENAME = _decoder.FLAC__FILE_ENCODER_NO_FILENAME
FLAC__FILE_ENCODER_SEEKABLE_STREAM_ENCODER_ERROR = _decoder.FLAC__FILE_ENCODER_SEEKABLE_STREAM_ENCODER_ERROR
FLAC__FILE_ENCODER_FATAL_ERROR_WHILE_WRITING = _decoder.FLAC__FILE_ENCODER_FATAL_ERROR_WHILE_WRITING
FLAC__FILE_ENCODER_ERROR_OPENING_FILE = _decoder.FLAC__FILE_ENCODER_ERROR_OPENING_FILE
FLAC__FILE_ENCODER_MEMORY_ALLOCATION_ERROR = _decoder.FLAC__FILE_ENCODER_MEMORY_ALLOCATION_ERROR
FLAC__FILE_ENCODER_ALREADY_INITIALIZED = _decoder.FLAC__FILE_ENCODER_ALREADY_INITIALIZED
FLAC__FILE_ENCODER_UNINITIALIZED = _decoder.FLAC__FILE_ENCODER_UNINITIALIZED
class FileEncoder(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FileEncoder, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FileEncoder, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__FileEncoder instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["protected_"] = _decoder.FileEncoder_protected__set
    __swig_getmethods__["protected_"] = _decoder.FileEncoder_protected__get
    if _newclass:protected_ = property(_decoder.FileEncoder_protected__get, _decoder.FileEncoder_protected__set)
    __swig_setmethods__["private_"] = _decoder.FileEncoder_private__set
    __swig_getmethods__["private_"] = _decoder.FileEncoder_private__get
    if _newclass:private_ = property(_decoder.FileEncoder_private__get, _decoder.FileEncoder_private__set)
    def __init__(self, *args):
        _swig_setattr(self, FileEncoder, 'this', _decoder.new_FileEncoder(*args))
        _swig_setattr(self, FileEncoder, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_FileEncoder):
        try:
            if self.thisown: destroy(self)
        except: pass


class FileEncoderPtr(FileEncoder):
    def __init__(self, this):
        _swig_setattr(self, FileEncoder, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FileEncoder, 'thisown', 0)
        _swig_setattr(self, FileEncoder,self.__class__,FileEncoder)
_decoder.FileEncoder_swigregister(FileEncoderPtr)

class Metadata(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Metadata, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Metadata, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["type"] = _decoder.Metadata_type_set
    __swig_getmethods__["type"] = _decoder.Metadata_type_get
    if _newclass:type = property(_decoder.Metadata_type_get, _decoder.Metadata_type_set)
    __swig_setmethods__["is_last"] = _decoder.Metadata_is_last_set
    __swig_getmethods__["is_last"] = _decoder.Metadata_is_last_get
    if _newclass:is_last = property(_decoder.Metadata_is_last_get, _decoder.Metadata_is_last_set)
    __swig_setmethods__["length"] = _decoder.Metadata_length_set
    __swig_getmethods__["length"] = _decoder.Metadata_length_get
    if _newclass:length = property(_decoder.Metadata_length_get, _decoder.Metadata_length_set)
    __swig_getmethods__["data"] = _decoder.Metadata_data_get
    if _newclass:data = property(_decoder.Metadata_data_get)
    def __init__(self, *args):
        _swig_setattr(self, Metadata, 'this', _decoder.new_Metadata(*args))
        _swig_setattr(self, Metadata, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_Metadata):
        try:
            if self.thisown: destroy(self)
        except: pass


class MetadataPtr(Metadata):
    def __init__(self, this):
        _swig_setattr(self, Metadata, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Metadata, 'thisown', 0)
        _swig_setattr(self, Metadata,self.__class__,Metadata)
_decoder.Metadata_swigregister(MetadataPtr)

class FLAC__StreamMetadata_data(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, FLAC__StreamMetadata_data, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, FLAC__StreamMetadata_data, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_data instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["stream_info"] = _decoder.FLAC__StreamMetadata_data_stream_info_set
    __swig_getmethods__["stream_info"] = _decoder.FLAC__StreamMetadata_data_stream_info_get
    if _newclass:stream_info = property(_decoder.FLAC__StreamMetadata_data_stream_info_get, _decoder.FLAC__StreamMetadata_data_stream_info_set)
    __swig_setmethods__["padding"] = _decoder.FLAC__StreamMetadata_data_padding_set
    __swig_getmethods__["padding"] = _decoder.FLAC__StreamMetadata_data_padding_get
    if _newclass:padding = property(_decoder.FLAC__StreamMetadata_data_padding_get, _decoder.FLAC__StreamMetadata_data_padding_set)
    __swig_setmethods__["application"] = _decoder.FLAC__StreamMetadata_data_application_set
    __swig_getmethods__["application"] = _decoder.FLAC__StreamMetadata_data_application_get
    if _newclass:application = property(_decoder.FLAC__StreamMetadata_data_application_get, _decoder.FLAC__StreamMetadata_data_application_set)
    __swig_setmethods__["seek_table"] = _decoder.FLAC__StreamMetadata_data_seek_table_set
    __swig_getmethods__["seek_table"] = _decoder.FLAC__StreamMetadata_data_seek_table_get
    if _newclass:seek_table = property(_decoder.FLAC__StreamMetadata_data_seek_table_get, _decoder.FLAC__StreamMetadata_data_seek_table_set)
    __swig_setmethods__["vorbis_comment"] = _decoder.FLAC__StreamMetadata_data_vorbis_comment_set
    __swig_getmethods__["vorbis_comment"] = _decoder.FLAC__StreamMetadata_data_vorbis_comment_get
    if _newclass:vorbis_comment = property(_decoder.FLAC__StreamMetadata_data_vorbis_comment_get, _decoder.FLAC__StreamMetadata_data_vorbis_comment_set)
    __swig_setmethods__["cue_sheet"] = _decoder.FLAC__StreamMetadata_data_cue_sheet_set
    __swig_getmethods__["cue_sheet"] = _decoder.FLAC__StreamMetadata_data_cue_sheet_get
    if _newclass:cue_sheet = property(_decoder.FLAC__StreamMetadata_data_cue_sheet_get, _decoder.FLAC__StreamMetadata_data_cue_sheet_set)
    __swig_setmethods__["unknown"] = _decoder.FLAC__StreamMetadata_data_unknown_set
    __swig_getmethods__["unknown"] = _decoder.FLAC__StreamMetadata_data_unknown_get
    if _newclass:unknown = property(_decoder.FLAC__StreamMetadata_data_unknown_get, _decoder.FLAC__StreamMetadata_data_unknown_set)
    def __init__(self, *args):
        _swig_setattr(self, FLAC__StreamMetadata_data, 'this', _decoder.new_FLAC__StreamMetadata_data(*args))
        _swig_setattr(self, FLAC__StreamMetadata_data, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_FLAC__StreamMetadata_data):
        try:
            if self.thisown: destroy(self)
        except: pass


class FLAC__StreamMetadata_dataPtr(FLAC__StreamMetadata_data):
    def __init__(self, this):
        _swig_setattr(self, FLAC__StreamMetadata_data, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, FLAC__StreamMetadata_data, 'thisown', 0)
        _swig_setattr(self, FLAC__StreamMetadata_data,self.__class__,FLAC__StreamMetadata_data)
_decoder.FLAC__StreamMetadata_data_swigregister(FLAC__StreamMetadata_dataPtr)

class StreamInfo(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, StreamInfo, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, StreamInfo, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_StreamInfo instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["min_blocksize"] = _decoder.StreamInfo_min_blocksize_set
    __swig_getmethods__["min_blocksize"] = _decoder.StreamInfo_min_blocksize_get
    if _newclass:min_blocksize = property(_decoder.StreamInfo_min_blocksize_get, _decoder.StreamInfo_min_blocksize_set)
    __swig_setmethods__["max_blocksize"] = _decoder.StreamInfo_max_blocksize_set
    __swig_getmethods__["max_blocksize"] = _decoder.StreamInfo_max_blocksize_get
    if _newclass:max_blocksize = property(_decoder.StreamInfo_max_blocksize_get, _decoder.StreamInfo_max_blocksize_set)
    __swig_setmethods__["min_framesize"] = _decoder.StreamInfo_min_framesize_set
    __swig_getmethods__["min_framesize"] = _decoder.StreamInfo_min_framesize_get
    if _newclass:min_framesize = property(_decoder.StreamInfo_min_framesize_get, _decoder.StreamInfo_min_framesize_set)
    __swig_setmethods__["max_framesize"] = _decoder.StreamInfo_max_framesize_set
    __swig_getmethods__["max_framesize"] = _decoder.StreamInfo_max_framesize_get
    if _newclass:max_framesize = property(_decoder.StreamInfo_max_framesize_get, _decoder.StreamInfo_max_framesize_set)
    __swig_setmethods__["sample_rate"] = _decoder.StreamInfo_sample_rate_set
    __swig_getmethods__["sample_rate"] = _decoder.StreamInfo_sample_rate_get
    if _newclass:sample_rate = property(_decoder.StreamInfo_sample_rate_get, _decoder.StreamInfo_sample_rate_set)
    __swig_setmethods__["channels"] = _decoder.StreamInfo_channels_set
    __swig_getmethods__["channels"] = _decoder.StreamInfo_channels_get
    if _newclass:channels = property(_decoder.StreamInfo_channels_get, _decoder.StreamInfo_channels_set)
    __swig_setmethods__["bits_per_sample"] = _decoder.StreamInfo_bits_per_sample_set
    __swig_getmethods__["bits_per_sample"] = _decoder.StreamInfo_bits_per_sample_get
    if _newclass:bits_per_sample = property(_decoder.StreamInfo_bits_per_sample_get, _decoder.StreamInfo_bits_per_sample_set)
    __swig_setmethods__["total_samples"] = _decoder.StreamInfo_total_samples_set
    __swig_getmethods__["total_samples"] = _decoder.StreamInfo_total_samples_get
    if _newclass:total_samples = property(_decoder.StreamInfo_total_samples_get, _decoder.StreamInfo_total_samples_set)
    __swig_setmethods__["md5sum"] = _decoder.StreamInfo_md5sum_set
    __swig_getmethods__["md5sum"] = _decoder.StreamInfo_md5sum_get
    if _newclass:md5sum = property(_decoder.StreamInfo_md5sum_get, _decoder.StreamInfo_md5sum_set)
    def __init__(self, *args):
        _swig_setattr(self, StreamInfo, 'this', _decoder.new_StreamInfo(*args))
        _swig_setattr(self, StreamInfo, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_StreamInfo):
        try:
            if self.thisown: destroy(self)
        except: pass


class StreamInfoPtr(StreamInfo):
    def __init__(self, this):
        _swig_setattr(self, StreamInfo, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, StreamInfo, 'thisown', 0)
        _swig_setattr(self, StreamInfo,self.__class__,StreamInfo)
_decoder.StreamInfo_swigregister(StreamInfoPtr)

class Padding(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Padding, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Padding, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Padding instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["dummy"] = _decoder.Padding_dummy_set
    __swig_getmethods__["dummy"] = _decoder.Padding_dummy_get
    if _newclass:dummy = property(_decoder.Padding_dummy_get, _decoder.Padding_dummy_set)
    def __init__(self, *args):
        _swig_setattr(self, Padding, 'this', _decoder.new_Padding(*args))
        _swig_setattr(self, Padding, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_Padding):
        try:
            if self.thisown: destroy(self)
        except: pass


class PaddingPtr(Padding):
    def __init__(self, this):
        _swig_setattr(self, Padding, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Padding, 'thisown', 0)
        _swig_setattr(self, Padding,self.__class__,Padding)
_decoder.Padding_swigregister(PaddingPtr)

class Application(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Application, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Application, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Application instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["id"] = _decoder.Application_id_set
    __swig_getmethods__["id"] = _decoder.Application_id_get
    if _newclass:id = property(_decoder.Application_id_get, _decoder.Application_id_set)
    __swig_setmethods__["data"] = _decoder.Application_data_set
    __swig_getmethods__["data"] = _decoder.Application_data_get
    if _newclass:data = property(_decoder.Application_data_get, _decoder.Application_data_set)
    def __init__(self, *args):
        _swig_setattr(self, Application, 'this', _decoder.new_Application(*args))
        _swig_setattr(self, Application, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_Application):
        try:
            if self.thisown: destroy(self)
        except: pass


class ApplicationPtr(Application):
    def __init__(self, this):
        _swig_setattr(self, Application, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Application, 'thisown', 0)
        _swig_setattr(self, Application,self.__class__,Application)
_decoder.Application_swigregister(ApplicationPtr)

class SeekPoint(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SeekPoint, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SeekPoint, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_SeekPoint instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["sample_number"] = _decoder.SeekPoint_sample_number_set
    __swig_getmethods__["sample_number"] = _decoder.SeekPoint_sample_number_get
    if _newclass:sample_number = property(_decoder.SeekPoint_sample_number_get, _decoder.SeekPoint_sample_number_set)
    __swig_setmethods__["stream_offset"] = _decoder.SeekPoint_stream_offset_set
    __swig_getmethods__["stream_offset"] = _decoder.SeekPoint_stream_offset_get
    if _newclass:stream_offset = property(_decoder.SeekPoint_stream_offset_get, _decoder.SeekPoint_stream_offset_set)
    __swig_setmethods__["frame_samples"] = _decoder.SeekPoint_frame_samples_set
    __swig_getmethods__["frame_samples"] = _decoder.SeekPoint_frame_samples_get
    if _newclass:frame_samples = property(_decoder.SeekPoint_frame_samples_get, _decoder.SeekPoint_frame_samples_set)
    def __init__(self, *args):
        _swig_setattr(self, SeekPoint, 'this', _decoder.new_SeekPoint(*args))
        _swig_setattr(self, SeekPoint, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_SeekPoint):
        try:
            if self.thisown: destroy(self)
        except: pass


class SeekPointPtr(SeekPoint):
    def __init__(self, this):
        _swig_setattr(self, SeekPoint, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, SeekPoint, 'thisown', 0)
        _swig_setattr(self, SeekPoint,self.__class__,SeekPoint)
_decoder.SeekPoint_swigregister(SeekPointPtr)

class SeekTable(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, SeekTable, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, SeekTable, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_SeekTable instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["num_points"] = _decoder.SeekTable_num_points_set
    __swig_getmethods__["num_points"] = _decoder.SeekTable_num_points_get
    if _newclass:num_points = property(_decoder.SeekTable_num_points_get, _decoder.SeekTable_num_points_set)
    __swig_setmethods__["points"] = _decoder.SeekTable_points_set
    __swig_getmethods__["points"] = _decoder.SeekTable_points_get
    if _newclass:points = property(_decoder.SeekTable_points_get, _decoder.SeekTable_points_set)
    def __init__(self, *args):
        _swig_setattr(self, SeekTable, 'this', _decoder.new_SeekTable(*args))
        _swig_setattr(self, SeekTable, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_SeekTable):
        try:
            if self.thisown: destroy(self)
        except: pass


class SeekTablePtr(SeekTable):
    def __init__(self, this):
        _swig_setattr(self, SeekTable, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, SeekTable, 'thisown', 0)
        _swig_setattr(self, SeekTable,self.__class__,SeekTable)
_decoder.SeekTable_swigregister(SeekTablePtr)

class VorbisCommentEntry(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, VorbisCommentEntry, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, VorbisCommentEntry, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_VorbisComment_Entry instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["length"] = _decoder.VorbisCommentEntry_length_set
    __swig_getmethods__["length"] = _decoder.VorbisCommentEntry_length_get
    if _newclass:length = property(_decoder.VorbisCommentEntry_length_get, _decoder.VorbisCommentEntry_length_set)
    __swig_setmethods__["entry"] = _decoder.VorbisCommentEntry_entry_set
    __swig_getmethods__["entry"] = _decoder.VorbisCommentEntry_entry_get
    if _newclass:entry = property(_decoder.VorbisCommentEntry_entry_get, _decoder.VorbisCommentEntry_entry_set)
    def __init__(self, *args):
        _swig_setattr(self, VorbisCommentEntry, 'this', _decoder.new_VorbisCommentEntry(*args))
        _swig_setattr(self, VorbisCommentEntry, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_VorbisCommentEntry):
        try:
            if self.thisown: destroy(self)
        except: pass


class VorbisCommentEntryPtr(VorbisCommentEntry):
    def __init__(self, this):
        _swig_setattr(self, VorbisCommentEntry, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, VorbisCommentEntry, 'thisown', 0)
        _swig_setattr(self, VorbisCommentEntry,self.__class__,VorbisCommentEntry)
_decoder.VorbisCommentEntry_swigregister(VorbisCommentEntryPtr)

class VorbisComment(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, VorbisComment, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, VorbisComment, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_VorbisComment instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["vendor_string"] = _decoder.VorbisComment_vendor_string_set
    __swig_getmethods__["vendor_string"] = _decoder.VorbisComment_vendor_string_get
    if _newclass:vendor_string = property(_decoder.VorbisComment_vendor_string_get, _decoder.VorbisComment_vendor_string_set)
    __swig_setmethods__["num_comments"] = _decoder.VorbisComment_num_comments_set
    __swig_getmethods__["num_comments"] = _decoder.VorbisComment_num_comments_get
    if _newclass:num_comments = property(_decoder.VorbisComment_num_comments_get, _decoder.VorbisComment_num_comments_set)
    __swig_setmethods__["comments"] = _decoder.VorbisComment_comments_set
    __swig_getmethods__["comments"] = _decoder.VorbisComment_comments_get
    if _newclass:comments = property(_decoder.VorbisComment_comments_get, _decoder.VorbisComment_comments_set)
    def __init__(self, *args):
        _swig_setattr(self, VorbisComment, 'this', _decoder.new_VorbisComment(*args))
        _swig_setattr(self, VorbisComment, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_VorbisComment):
        try:
            if self.thisown: destroy(self)
        except: pass


class VorbisCommentPtr(VorbisComment):
    def __init__(self, this):
        _swig_setattr(self, VorbisComment, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, VorbisComment, 'thisown', 0)
        _swig_setattr(self, VorbisComment,self.__class__,VorbisComment)
_decoder.VorbisComment_swigregister(VorbisCommentPtr)

class CueSheetIndex(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheetIndex, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheetIndex, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet_Index instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["offset"] = _decoder.CueSheetIndex_offset_set
    __swig_getmethods__["offset"] = _decoder.CueSheetIndex_offset_get
    if _newclass:offset = property(_decoder.CueSheetIndex_offset_get, _decoder.CueSheetIndex_offset_set)
    __swig_setmethods__["number"] = _decoder.CueSheetIndex_number_set
    __swig_getmethods__["number"] = _decoder.CueSheetIndex_number_get
    if _newclass:number = property(_decoder.CueSheetIndex_number_get, _decoder.CueSheetIndex_number_set)
    def __init__(self, *args):
        _swig_setattr(self, CueSheetIndex, 'this', _decoder.new_CueSheetIndex(*args))
        _swig_setattr(self, CueSheetIndex, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_CueSheetIndex):
        try:
            if self.thisown: destroy(self)
        except: pass


class CueSheetIndexPtr(CueSheetIndex):
    def __init__(self, this):
        _swig_setattr(self, CueSheetIndex, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheetIndex, 'thisown', 0)
        _swig_setattr(self, CueSheetIndex,self.__class__,CueSheetIndex)
_decoder.CueSheetIndex_swigregister(CueSheetIndexPtr)

class CueSheetTrack(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheetTrack, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheetTrack, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet_Track instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["offset"] = _decoder.CueSheetTrack_offset_set
    __swig_getmethods__["offset"] = _decoder.CueSheetTrack_offset_get
    if _newclass:offset = property(_decoder.CueSheetTrack_offset_get, _decoder.CueSheetTrack_offset_set)
    __swig_setmethods__["number"] = _decoder.CueSheetTrack_number_set
    __swig_getmethods__["number"] = _decoder.CueSheetTrack_number_get
    if _newclass:number = property(_decoder.CueSheetTrack_number_get, _decoder.CueSheetTrack_number_set)
    __swig_setmethods__["isrc"] = _decoder.CueSheetTrack_isrc_set
    __swig_getmethods__["isrc"] = _decoder.CueSheetTrack_isrc_get
    if _newclass:isrc = property(_decoder.CueSheetTrack_isrc_get, _decoder.CueSheetTrack_isrc_set)
    __swig_setmethods__["type"] = _decoder.CueSheetTrack_type_set
    __swig_getmethods__["type"] = _decoder.CueSheetTrack_type_get
    if _newclass:type = property(_decoder.CueSheetTrack_type_get, _decoder.CueSheetTrack_type_set)
    __swig_setmethods__["pre_emphasis"] = _decoder.CueSheetTrack_pre_emphasis_set
    __swig_getmethods__["pre_emphasis"] = _decoder.CueSheetTrack_pre_emphasis_get
    if _newclass:pre_emphasis = property(_decoder.CueSheetTrack_pre_emphasis_get, _decoder.CueSheetTrack_pre_emphasis_set)
    __swig_setmethods__["num_indices"] = _decoder.CueSheetTrack_num_indices_set
    __swig_getmethods__["num_indices"] = _decoder.CueSheetTrack_num_indices_get
    if _newclass:num_indices = property(_decoder.CueSheetTrack_num_indices_get, _decoder.CueSheetTrack_num_indices_set)
    __swig_setmethods__["indices"] = _decoder.CueSheetTrack_indices_set
    __swig_getmethods__["indices"] = _decoder.CueSheetTrack_indices_get
    if _newclass:indices = property(_decoder.CueSheetTrack_indices_get, _decoder.CueSheetTrack_indices_set)
    def __init__(self, *args):
        _swig_setattr(self, CueSheetTrack, 'this', _decoder.new_CueSheetTrack(*args))
        _swig_setattr(self, CueSheetTrack, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_CueSheetTrack):
        try:
            if self.thisown: destroy(self)
        except: pass


class CueSheetTrackPtr(CueSheetTrack):
    def __init__(self, this):
        _swig_setattr(self, CueSheetTrack, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheetTrack, 'thisown', 0)
        _swig_setattr(self, CueSheetTrack,self.__class__,CueSheetTrack)
_decoder.CueSheetTrack_swigregister(CueSheetTrackPtr)

class CueSheet(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, CueSheet, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, CueSheet, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_CueSheet instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["media_catalog_number"] = _decoder.CueSheet_media_catalog_number_set
    __swig_getmethods__["media_catalog_number"] = _decoder.CueSheet_media_catalog_number_get
    if _newclass:media_catalog_number = property(_decoder.CueSheet_media_catalog_number_get, _decoder.CueSheet_media_catalog_number_set)
    __swig_setmethods__["lead_in"] = _decoder.CueSheet_lead_in_set
    __swig_getmethods__["lead_in"] = _decoder.CueSheet_lead_in_get
    if _newclass:lead_in = property(_decoder.CueSheet_lead_in_get, _decoder.CueSheet_lead_in_set)
    __swig_setmethods__["is_cd"] = _decoder.CueSheet_is_cd_set
    __swig_getmethods__["is_cd"] = _decoder.CueSheet_is_cd_get
    if _newclass:is_cd = property(_decoder.CueSheet_is_cd_get, _decoder.CueSheet_is_cd_set)
    __swig_setmethods__["num_tracks"] = _decoder.CueSheet_num_tracks_set
    __swig_getmethods__["num_tracks"] = _decoder.CueSheet_num_tracks_get
    if _newclass:num_tracks = property(_decoder.CueSheet_num_tracks_get, _decoder.CueSheet_num_tracks_set)
    __swig_setmethods__["tracks"] = _decoder.CueSheet_tracks_set
    __swig_getmethods__["tracks"] = _decoder.CueSheet_tracks_get
    if _newclass:tracks = property(_decoder.CueSheet_tracks_get, _decoder.CueSheet_tracks_set)
    def __init__(self, *args):
        _swig_setattr(self, CueSheet, 'this', _decoder.new_CueSheet(*args))
        _swig_setattr(self, CueSheet, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_CueSheet):
        try:
            if self.thisown: destroy(self)
        except: pass


class CueSheetPtr(CueSheet):
    def __init__(self, this):
        _swig_setattr(self, CueSheet, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, CueSheet, 'thisown', 0)
        _swig_setattr(self, CueSheet,self.__class__,CueSheet)
_decoder.CueSheet_swigregister(CueSheetPtr)

class Unknown(_object):
    __swig_setmethods__ = {}
    __setattr__ = lambda self, name, value: _swig_setattr(self, Unknown, name, value)
    __swig_getmethods__ = {}
    __getattr__ = lambda self, name: _swig_getattr(self, Unknown, name)
    def __repr__(self):
        return "<%s.%s; proxy of C FLAC__StreamMetadata_Unknown instance at %s>" % (self.__class__.__module__, self.__class__.__name__, self.this,)
    __swig_setmethods__["data"] = _decoder.Unknown_data_set
    __swig_getmethods__["data"] = _decoder.Unknown_data_get
    if _newclass:data = property(_decoder.Unknown_data_get, _decoder.Unknown_data_set)
    def __init__(self, *args):
        _swig_setattr(self, Unknown, 'this', _decoder.new_Unknown(*args))
        _swig_setattr(self, Unknown, 'thisown', 1)
    def __del__(self, destroy=_decoder.delete_Unknown):
        try:
            if self.thisown: destroy(self)
        except: pass


class UnknownPtr(Unknown):
    def __init__(self, this):
        _swig_setattr(self, Unknown, 'this', this)
        if not hasattr(self,"thisown"): _swig_setattr(self, Unknown, 'thisown', 0)
        _swig_setattr(self, Unknown,self.__class__,Unknown)
_decoder.Unknown_swigregister(UnknownPtr)

STREAMINFO = _decoder.STREAMINFO
PADDING = _decoder.PADDING
APPLICATION = _decoder.APPLICATION
SEEKTABLE = _decoder.SEEKTABLE
VORBIS_COMMENT = _decoder.VORBIS_COMMENT
CUESHEET = _decoder.CUESHEET
UNDEFINED = _decoder.UNDEFINED
FLAC__METADATA_CHAIN_STATUS_OK = _decoder.FLAC__METADATA_CHAIN_STATUS_OK
FLAC__METADATA_CHAIN_STATUS_ILLEGAL_INPUT = _decoder.FLAC__METADATA_CHAIN_STATUS_ILLEGAL_INPUT
FLAC__METADATA_CHAIN_STATUS_ERROR_OPENING_FILE = _decoder.FLAC__METADATA_CHAIN_STATUS_ERROR_OPENING_FILE
FLAC__METADATA_CHAIN_STATUS_NOT_A_FLAC_FILE = _decoder.FLAC__METADATA_CHAIN_STATUS_NOT_A_FLAC_FILE
FLAC__METADATA_CHAIN_STATUS_NOT_WRITABLE = _decoder.FLAC__METADATA_CHAIN_STATUS_NOT_WRITABLE
FLAC__METADATA_CHAIN_STATUS_BAD_METADATA = _decoder.FLAC__METADATA_CHAIN_STATUS_BAD_METADATA
FLAC__METADATA_CHAIN_STATUS_READ_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_READ_ERROR
FLAC__METADATA_CHAIN_STATUS_SEEK_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_SEEK_ERROR
FLAC__METADATA_CHAIN_STATUS_WRITE_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_WRITE_ERROR
FLAC__METADATA_CHAIN_STATUS_RENAME_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_RENAME_ERROR
FLAC__METADATA_CHAIN_STATUS_UNLINK_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_UNLINK_ERROR
FLAC__METADATA_CHAIN_STATUS_MEMORY_ALLOCATION_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_MEMORY_ALLOCATION_ERROR
FLAC__METADATA_CHAIN_STATUS_INTERNAL_ERROR = _decoder.FLAC__METADATA_CHAIN_STATUS_INTERNAL_ERROR
NullWriteCallBack = _decoder.NullWriteCallBack
NullMetadataCallBack = _decoder.NullMetadataCallBack
NullErrorCallBack = _decoder.NullErrorCallBack
PythonWriteCallBack = _decoder.PythonWriteCallBack
PythonMetadataCallBack = _decoder.PythonMetadataCallBack
PythonErrorCallBack = _decoder.PythonErrorCallBack
cvar = _decoder.cvar

