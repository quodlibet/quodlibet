/*
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
*/
%module decoder

%typemap(python,in) PyObject *pyfunc {
  if (!PyCallable_Check($input)) {
      PyErr_SetString(PyExc_TypeError, "Need a callable object");
      return NULL;
  }
  $1 = $input;
}

%{

#include <FLAC/format.h>
#include <FLAC/file_decoder.h>

// Python Callback Functions Stuff
PyObject *callbacks[3];

FLAC__StreamDecoderWriteStatus PythonWriteCallBack(const FLAC__FileDecoder *decoder, const FLAC__Frame *frame, const FLAC__int32 *const buffer[], void *client_data) {

    // Interleave the audio and return a single buffer object to python
    FLAC__uint32 data_size = frame->header.blocksize * frame->header.channels 
                        * (frame->header.bits_per_sample / 8);

    FLAC__uint16 ldb[frame->header.blocksize * frame->header.channels];
    int c_samp, c_chan, d_samp;

    for(c_samp = d_samp = 0; c_samp < frame->header.blocksize; c_samp++) {
        for(c_chan = 0; c_chan < frame->header.channels; c_chan++, d_samp++) {
            ldb[d_samp] = buffer[c_chan][c_samp];
        }
    }

   PyObject *arglist;
   PyObject *result;
   FLAC__StreamDecoderWriteStatus res;
   PyObject *dec, *buf;

   dec = SWIG_NewPointerObj((void *) decoder, SWIGTYPE_p_FLAC__FileDecoder, 0);
   buf = PyBuffer_FromMemory((void *) ldb, data_size);
   arglist = Py_BuildValue("(OOl)", dec, buf, data_size);
   result = PyEval_CallObject(callbacks[0],arglist);

   Py_DECREF(buf);
   Py_DECREF(dec);
   Py_DECREF(arglist);
   if (result) {
     res = PyInt_AsLong(result);
   }
   Py_XDECREF(result);
   return res;
}

void PythonMetadataCallBack(const FLAC__FileDecoder *decoder, const FLAC__StreamMetadata *metadata, void *client_data) {
   PyObject *arglist;
   PyObject *dec, *meta;
   dec = SWIG_NewPointerObj((void *) decoder, SWIGTYPE_p_FLAC__FileDecoder, 0);
   meta = SWIG_NewPointerObj((void *) metadata, SWIGTYPE_p_FLAC__StreamMetadata, 0);
   arglist = Py_BuildValue("(OO)", dec, meta);

   PyEval_CallObject(callbacks[2],arglist);
   Py_DECREF(dec);
   Py_DECREF(meta);
   Py_DECREF(arglist);
}

void PythonErrorCallBack(const FLAC__FileDecoder *decoder, FLAC__StreamDecoderErrorStatus status, void *client_data) {
   PyObject *arglist;
   PyObject *dec, *stat;
   dec = SWIG_NewPointerObj((void *) decoder, SWIGTYPE_p_FLAC__FileDecoder, 0);
   stat = PyCObject_FromVoidPtr((void *)status, NULL);
   arglist = Py_BuildValue("(OO)", dec, stat);
   
   PyEval_CallObject(callbacks[1], arglist);
   Py_DECREF(dec);
   Py_DECREF(stat);
   Py_DECREF(arglist);
}

// Simple Callbacks (for testing etc)

FLAC__StreamDecoderWriteStatus NullWriteCallBack(const FLAC__FileDecoder *decoder, const FLAC__Frame *frame, const FLAC__int32 *const buffer[], void *client_data) {
    //printf("Inside C write cb\n");
    return FLAC__FILE_DECODER_OK;
}

void NullMetadataCallBack(const FLAC__FileDecoder *decoder, const FLAC__StreamMetadata *metadata, void *client_data) {
    //printf("Inside C metadata cb\n");
}

void NullErrorCallBack(const FLAC__FileDecoder *decoder, FLAC__StreamDecoderErrorStatus status, void *client_data) {
    //printf("Inside C error cb\n");
}

%}

%include "flac/format.i"

PyObject *callbacks[3];

%extend FLAC__FileDecoder {
    FLAC__FileDecoder() {
        return FLAC__file_decoder_new();
    }
//    ~FLAC__FileDecoder() {
    void delete() {
        FLAC__file_decoder_delete(self);
    }
    FLAC__bool set_md5_checking(FLAC__bool value) {
        return FLAC__file_decoder_set_md5_checking(self, value);
    }
    FLAC__bool set_filename(char *fname) {
        return FLAC__file_decoder_set_filename(self, fname);
    }
    FLAC__bool set_write_callback(PyObject *pyfunc) {
        callbacks[0] = pyfunc;
        Py_INCREF(pyfunc);
        return FLAC__file_decoder_set_write_callback(self, PythonWriteCallBack);
    }
    FLAC__bool set_error_callback(PyObject *pyfunc) {
        callbacks[1] = pyfunc;
        Py_INCREF(pyfunc);
        return FLAC__file_decoder_set_error_callback(self, PythonErrorCallBack);
    }
    FLAC__bool set_metadata_callback(PyObject *pyfunc) {
        callbacks[2] = pyfunc;
        Py_INCREF(pyfunc);
        return FLAC__file_decoder_set_metadata_callback(self, PythonMetadataCallBack);
    }
    FLAC__bool 	set_metadata_respond_all() {
        return FLAC__file_decoder_set_metadata_respond_all(self);
    }
    FLAC__bool 	set_metadata_respond(FLAC__MetadataType type) {
        return FLAC__file_decoder_set_metadata_respond(self, type);
    }
    FLAC__bool set_metadata_respond_application(const FLAC__byte id[4]) {
        return FLAC__file_decoder_set_metadata_respond_application(self, id);
    }
    FLAC__bool 	set_metadata_ignore_all() {
        return FLAC__file_decoder_set_metadata_ignore_all(self);
    }
    FLAC__bool 	set_metadata_ignore(FLAC__MetadataType type) {
        return FLAC__file_decoder_set_metadata_ignore(self, type);
    }
    FLAC__bool set_metadata_ignore_application(const FLAC__byte id[4]) {
        return FLAC__file_decoder_set_metadata_ignore_application(self, id);
    }
    FLAC__FileDecoderState get_state() {
        return FLAC__file_decoder_get_state(self);
    }
    FLAC__SeekableStreamDecoderState get_seekable_stream_decoder_state() {
        return FLAC__file_decoder_get_seekable_stream_decoder_state(self);
    }
    FLAC__StreamDecoderState get_stream_decoder_state() {
        return FLAC__file_decoder_get_stream_decoder_state(self);
    }
    const char *get_resolved_state_string() {
        return FLAC__file_decoder_get_resolved_state_string(self);
    }
    FLAC__bool get_md5_checking() {
        return FLAC__file_decoder_get_md5_checking(self);
    }
    FLAC__ChannelAssignment get_channel_assignment() {
        return FLAC__file_decoder_get_channel_assignment(self);
    }
    unsigned get_channels() {
        return FLAC__file_decoder_get_channels (self);
    }
    unsigned get_bits_per_sample() {
        return FLAC__file_decoder_get_bits_per_sample(self);
    }
    unsigned get_sample_rate() {
        return FLAC__file_decoder_get_sample_rate(self);
    }
    unsigned get_blocksize() {
        return FLAC__file_decoder_get_blocksize(self);
    }
    FLAC__uint64 get_decode_position() {
        FLAC__uint64 tmp;
        FLAC__file_decoder_get_decode_position(self, &tmp);
        return tmp;
    }
    FLAC__FileDecoderState init() {
        return FLAC__file_decoder_init(self);
    }
    FLAC__bool finish() {
        return FLAC__file_decoder_finish(self);
    }
    FLAC__bool process_single() {
        return FLAC__file_decoder_process_single(self);
    }
    FLAC__bool process_until_end_of_metadata() {
        return FLAC__file_decoder_process_until_end_of_metadata (self);
    }
    FLAC__bool process_until_end_of_file() {
        return FLAC__file_decoder_process_until_end_of_file(self);
    }
    FLAC__bool seek_absolute(FLAC__uint64 sample) {
        return FLAC__file_decoder_seek_absolute(self, sample);
    }
}
        
// callbacks
typedef FLAC__StreamDecoderWriteStatus(* 	FLAC__FileDecoderWriteCallback )(const FLAC__FileDecoder *decoder, const FLAC__Frame *frame, const FLAC__int32 *const buffer[], void *client_data);
typedef void(* 	FLAC__FileDecoderMetadataCallback )(const FLAC__FileDecoder *decoder, const FLAC__StreamMetadata *metadata, void *client_data);
typedef void(* 	FLAC__FileDecoderErrorCallback )(const FLAC__FileDecoder *decoder, FLAC__StreamDecoderErrorStatus status, void *client_data);

// File decoder methods
// Most have now all been replaced by '%extend'ing the struct above

//FLAC__FileDecoder *FLAC__file_decoder_new ();
//void 	FLAC__file_decoder_delete (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_set_md5_checking (FLAC__FileDecoder *decoder, FLAC__bool value);
//FLAC__bool 	FLAC__file_decoder_set_filename (FLAC__FileDecoder *decoder, const char *value);
//FLAC__bool 	FLAC__file_decoder_set_write_callback (FLAC__FileDecoder *decoder, FLAC__FileDecoderWriteCallback value);
//FLAC__bool 	FLAC__file_decoder_set_metadata_callback (FLAC__FileDecoder *decoder, FLAC__FileDecoderMetadataCallback value);
//FLAC__bool 	FLAC__file_decoder_set_error_callback (FLAC__FileDecoder *decoder, FLAC__FileDecoderErrorCallback value);
//FLAC__bool 	FLAC__file_decoder_set_client_data (FLAC__FileDecoder *decoder, void *value);
//FLAC__bool 	FLAC__file_decoder_set_metadata_respond (FLAC__FileDecoder *decoder, FLAC__MetadataType type);
//FLAC__bool 	FLAC__file_decoder_set_metadata_respond_application (FLAC__FileDecoder *decoder, const FLAC__byte id[4]);
//FLAC__bool 	FLAC__file_decoder_set_metadata_respond_all (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_set_metadata_ignore (FLAC__FileDecoder *decoder, FLAC__MetadataType type);
//FLAC__bool 	FLAC__file_decoder_set_metadata_ignore_application (FLAC__FileDecoder *decoder, const FLAC__byte id[4]);
//FLAC__bool 	FLAC__file_decoder_set_metadata_ignore_all (FLAC__FileDecoder *decoder);
//FLAC__FileDecoderState 	FLAC__file_decoder_get_state (const FLAC__FileDecoder *decoder);
//FLAC__SeekableStreamDecoderState 	FLAC__file_decoder_get_seekable_stream_decoder_state (const FLAC__FileDecoder *decoder);
//FLAC__StreamDecoderState 	FLAC__file_decoder_get_stream_decoder_state (const FLAC__FileDecoder *decoder);
//const char * 	FLAC__file_decoder_get_resolved_state_string (const FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_get_md5_checking (const FLAC__FileDecoder *decoder);
//unsigned 	FLAC__file_decoder_get_channels (const FLAC__FileDecoder *decoder);
//FLAC__ChannelAssignment 	FLAC__file_decoder_get_channel_assignment (const FLAC__FileDecoder *decoder);
//unsigned 	FLAC__file_decoder_get_bits_per_sample (const FLAC__FileDecoder *decoder);
//unsigned 	FLAC__file_decoder_get_sample_rate (const FLAC__FileDecoder *decoder);
//unsigned 	FLAC__file_decoder_get_blocksize (const FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_get_decode_position (const FLAC__FileDecoder *decoder, FLAC__uint64 *position);
//FLAC__FileDecoderState 	FLAC__file_decoder_init (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_finish (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_process_single (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_process_until_end_of_metadata (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_process_until_end_of_file (FLAC__FileDecoder *decoder);
//FLAC__bool 	FLAC__file_decoder_seek_absolute (FLAC__FileDecoder *decoder, FLAC__uint64 sample);

// My extra stuff (see above)
%constant FLAC__StreamDecoderWriteStatus NullWriteCallBack(const FLAC__FileDecoder *decoder, const FLAC__Frame *frame, const FLAC__int32 *const buffer[], void *client_data);
%constant void NullMetadataCallBack(const FLAC__FileDecoder *decoder, const FLAC__StreamMetadata *metadata, void *client_data);
%constant void NullErrorCallBack(const FLAC__FileDecoder *decoder, FLAC__StreamDecoderErrorStatus status, void *client_data);
%constant FLAC__StreamDecoderWriteStatus PythonWriteCallBack(const FLAC__FileDecoder *decoder, const FLAC__Frame *frame, const FLAC__int32 *const buffer[], void *client_data);
%constant void PythonMetadataCallBack(const FLAC__FileDecoder *decoder, const FLAC__StreamMetadata *metadata, void *client_data);
%constant void PythonErrorCallBack(const FLAC__FileDecoder *decoder, FLAC__StreamDecoderErrorStatus status, void *client_data);
