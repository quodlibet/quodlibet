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
%module encoder

%typemap(python,in) PyObject *pyfunc {
    if (!PyCallable_Check($input)) {
        PyErr_SetString(PyExc_TypeError, "Need a callable object");
        return NULL;
    }
    $1 = $input;
}

%typemap(python,in) const void *byte_data {
    int ret, length;
    ret = PyObject_AsReadBuffer($input, (const void **)&$1, &length);
    if(ret != 0) {
        PyErr_SetString(PyExc_TypeError, "unable to get pointer from buffer");
        return NULL;
    }
}

%typemap(python, in) FLAC__StreamMetadata **metadata {
    int i, size;
    FLAC__StreamMetadata *tmp_blk;
    PyObject *tmp_obj;
    if(!PyTuple_Check($input)) {
        PyErr_SetString(PyExc_TypeError, "Expected a Tuple");
        return NULL;
    }
    // extract the tuple and create a FLAC__StreamMetadata **
    size = PyTuple_Size($input);
    FLAC__StreamMetadata **meta = calloc(sizeof(FLAC__StreamMetadata *), size);
    
    for(i=0; i<size; i++) {
        tmp_obj = PyTuple_GetItem($input, i);
        if ((SWIG_ConvertPtr(tmp_obj,(void **) &tmp_blk, SWIGTYPE_p_FLAC__StreamMetadata,SWIG_POINTER_EXCEPTION | 0 )) == -1) SWIG_fail;
        meta[i] = tmp_blk;
    }
    $1 = meta;
}

%{
#include <FLAC/format.h>
#include <FLAC/file_encoder.h>

void PythonProgressCallBack(const FLAC__FileEncoder *encoder, FLAC__uint64 bytes_written, FLAC__uint64 samples_written, unsigned frames_written, unsigned total_frames_estimate, void *client_data) {
//    printf("bytes written: %lu\n", bytes_written);
//    printf("samples written: %lu\n", samples_written);
//    printf("frames written: %u\n", frames_written);
//    printf("total_frames estimate: %u\n", total_frames_estimate);
   PyObject *arglist;
   PyObject *enc, *meta;
   PyObject *func;
   func = (PyObject *) client_data;
   enc = SWIG_NewPointerObj((void *) encoder, SWIGTYPE_p_FLAC__FileEncoder, 0);
   arglist = Py_BuildValue("(Ollii)", enc, (long)bytes_written, (long)samples_written, (int)frames_written, (int)total_frames_estimate);

   PyEval_CallObject(func,arglist);
   Py_DECREF(enc);
   Py_DECREF(arglist);
}

%}

%include "flac/format.i"

typedef void (*FLAC__FileEncoderProgressCallback)(const FLAC__FileEncoder *encoder, FLAC__uint64 bytes_written, FLAC__uint64 samples_written, unsigned frames_written, unsigned total_frames_estimate, void *client_data);

%extend FLAC__FileEncoder {
    FLAC__FileEncoder() {
        return FLAC__file_encoder_new();
    }
//    void delete() {
//        return FLAC__file_encoder_delete(self);
//    }
    FLAC__bool set_verify(FLAC__bool value) {
        return FLAC__file_encoder_set_verify(self, value);
    }
    FLAC__bool set_streamable_subset(FLAC__bool value) {
        return FLAC__file_encoder_set_streamable_subset(self, value);
    }
    FLAC__bool set_do_mid_side_stereo(FLAC__bool value) {
        return FLAC__file_encoder_set_do_mid_side_stereo(self, value);
    }
    FLAC__bool set_loose_mid_side_stereo(FLAC__bool value) {
        return FLAC__file_encoder_set_loose_mid_side_stereo(self, value);
    }
    FLAC__bool set_channels(unsigned value) {
        return FLAC__file_encoder_set_channels(self, value);
    }
    FLAC__bool set_bits_per_sample(unsigned value) {
        return FLAC__file_encoder_set_bits_per_sample(self, value);
    }
    FLAC__bool set_sample_rate(unsigned value) {
        return FLAC__file_encoder_set_sample_rate(self, value);
    }
    FLAC__bool set_blocksize(unsigned value) {
        return FLAC__file_encoder_set_blocksize(self, value);
    }
    FLAC__bool set_max_lpc_order(unsigned value) {
        return FLAC__file_encoder_set_max_lpc_order(self, value);
    }
    FLAC__bool set_qlp_coeff_precision(unsigned value) {
        return FLAC__file_encoder_set_qlp_coeff_precision(self, value);
    }
    FLAC__bool set_do_qlp_coeff_prec_search(FLAC__bool value) {
        return FLAC__file_encoder_set_do_qlp_coeff_prec_search(self, value);
    }
    FLAC__bool set_do_escape_coding(FLAC__bool value) {
        return FLAC__file_encoder_set_do_escape_coding(self, value);
    }
    FLAC__bool set_do_exhaustive_model_search(FLAC__bool value) {
        return FLAC__file_encoder_set_do_exhaustive_model_search(self, value);
    }
    FLAC__bool set_min_residual_partition_order(unsigned value) {
        return FLAC__file_encoder_set_min_residual_partition_order(self, value);
    }
    FLAC__bool set_max_residual_partition_order(unsigned value) {
        return FLAC__file_encoder_set_max_residual_partition_order(self, value);
    }
    FLAC__bool set_rice_parameter_search_dist(unsigned value) {
        return FLAC__file_encoder_set_rice_parameter_search_dist(self, value);
    }
//    FLAC__bool set_total_samples_estimate(FLAC__uint64 value) {
    FLAC__bool set_total_samples_estimate(FLAC__int64 value) {
        return FLAC__file_encoder_set_total_samples_estimate(self, value);
    }
    FLAC__bool set_metadata(FLAC__StreamMetadata **metadata, unsigned num_blocks) {
        return FLAC__file_encoder_set_metadata(self, metadata, num_blocks);
    }
    FLAC__bool set_filename(const char *value) {
        return FLAC__file_encoder_set_filename(self, value);
    }
    FLAC__bool set_progress_callback(PyObject *pyfunc) {
        FLAC__bool ret = FLAC__file_encoder_set_client_data(self, (void *)pyfunc);
        if(ret == true) {
            Py_INCREF(pyfunc);
            return FLAC__file_encoder_set_progress_callback(self, PythonProgressCallBack);
        }
        return ret;
    }
//    FLAC__bool set_client_data(void *value) {
//        return FLAC__file_encoder_set_client_data(self, value);
//    }
    FLAC__FileEncoderState get_state() {
        return FLAC__file_encoder_get_state(self);
    }
    FLAC__SeekableStreamEncoderState get_seekable_stream_encoder_state() {
        return FLAC__file_encoder_get_seekable_stream_encoder_state(self);
    }
    FLAC__StreamEncoderState get_stream_encoder_state() {
        return FLAC__file_encoder_get_stream_encoder_state(self);
    }
    FLAC__StreamDecoderState get_verify_decoder_state() {
        return FLAC__file_encoder_get_verify_decoder_state(self);
    }
    const char *get_resolved_state_string() {
        return FLAC__file_encoder_get_resolved_state_string(self);
    }
    void get_verify_decoder_error_stats(FLAC__uint64 *absolute_sample, unsigned *frame_number, unsigned *channel, unsigned *sample, FLAC__int32 *expected, FLAC__int32 *got) {
        return FLAC__file_encoder_get_verify_decoder_error_stats(self, absolute_sample, frame_number, channel, sample, expected, got);
    }
    FLAC__bool get_verify() {
        return FLAC__file_encoder_get_verify(self);
    }
    FLAC__bool get_streamable_subset() {
        return FLAC__file_encoder_get_streamable_subset(self);
    }
    FLAC__bool get_do_mid_side_stereo() {
        return FLAC__file_encoder_get_do_mid_side_stereo(self);
    }
    FLAC__bool get_loose_mid_side_stereo() {
        return FLAC__file_encoder_get_loose_mid_side_stereo(self);
    }
    unsigned get_channels() {
        return FLAC__file_encoder_get_channels(self);
    }
    unsigned get_bits_per_sample() {
        return FLAC__file_encoder_get_bits_per_sample(self);
    }
    unsigned get_sample_rate() {
        return FLAC__file_encoder_get_sample_rate(self);
    }
    unsigned get_blocksize() {
        return FLAC__file_encoder_get_blocksize(self);
    }
    unsigned get_max_lpc_order() {
        return FLAC__file_encoder_get_max_lpc_order(self);
    }
    unsigned get_qlp_coeff_precision() {
        return FLAC__file_encoder_get_qlp_coeff_precision(self);
    }
    FLAC__bool get_do_qlp_coeff_prec_search() {
        return FLAC__file_encoder_get_do_qlp_coeff_prec_search(self);
    }
    FLAC__bool get_do_escape_coding() {
        return FLAC__file_encoder_get_do_escape_coding(self);
    }
    FLAC__bool get_do_exhaustive_model_search() {
        return FLAC__file_encoder_get_do_exhaustive_model_search(self);
    }
    unsigned get_min_residual_partition_order() {
        return FLAC__file_encoder_get_min_residual_partition_order(self);
    }
    unsigned get_max_residual_partition_order() {
        return FLAC__file_encoder_get_max_residual_partition_order(self);
    }
    unsigned get_rice_parameter_search_dist() {
        return FLAC__file_encoder_get_rice_parameter_search_dist(self);
    }
    FLAC__uint64 get_total_samples_estimate() {
        return FLAC__file_encoder_get_total_samples_estimate(self);
    }
    FLAC__FileEncoderState init() {
        return FLAC__file_encoder_init(self);
    }
    void finish() {
        return FLAC__file_encoder_finish(self);
    }
    FLAC__bool process(const void *byte_data, unsigned samples) {
        FLAC__bool retval;
        int i,j;
        int channels = FLAC__file_encoder_get_channels(self);
        int width = FLAC__file_encoder_get_bits_per_sample(self);
        FLAC__int32 *buff = calloc(channels * samples, sizeof(FLAC__int32));

        // convert from input sample size to FLAC__int32
        if (width == 8) {
            FLAC__int8 *data = (FLAC__int8 *) byte_data;
            for(i=0; i< samples*channels; i++) {
                buff[i] = data[i];
            }
        }
        else if(width == 16) {
            FLAC__int16 *data = (FLAC__int16 *) byte_data;
            for(i=0; i< samples*channels; i++) {
                buff[i] = data[i];
            }
        }
        else if(width == 24) {
            FLAC__int8 *data = (FLAC__int8 *) byte_data;
            for(i=j=0; i<samples*channels; i++) {
                buff[i] = data[j++]; buff[i] <<= 8;
                buff[i] |= data[j++]; buff[i] <<= 8;
                buff[i] |= data[j++];
            }
        }
        else {
            printf("unsupported sample size\n");
            free(buff);
            return false;
        }
        retval = FLAC__file_encoder_process_interleaved(self, buff, samples);
        free(buff);
        return retval;
    }
//    FLAC__bool process_interleaved(const FLAC__int32 buffer[], unsigned samples) {
//        return FLAC__file_encoder_process_interleaved(self, buffer, samples);
//    }
}
