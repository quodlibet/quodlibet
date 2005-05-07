/* A Musepack (MPC) decoder wrapper for Python
   Uses libmpcdec, http://www.musepack.net/index.php?pg=src
   Copyright 2005 Joe Wreschnig, Wim Speekenbrink

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.

   $Id$
*/

#include <Python.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <string.h>
#include <fcntl.h>
#include <mpcdec/mpcdec.h>
#include <mpcdec/reader.h>
#include <structmember.h>

typedef struct {
  PyObject_HEAD
  mpc_decoder *decoder;
  mpc_reader_file *reader;

  int frequency;
  int channels;
  unsigned int frames;
  unsigned int samples;
  double bitrate;

  int stream_version;
  int encoder_version;
  char *encoder;
  int profile;
  char *profile_name;

  int gain_radio;
  int gain_audiophile;
  unsigned int peak_radio;
  unsigned int peak_audiophile;

  unsigned int length;
  double position;
} MPCFile;

static PyObject
*MPCFile_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  MPCFile *self;

  self = (MPCFile *)type->tp_alloc(type, 0);
  if (self != NULL) {
    self->length = 0;
    self->reader = NULL;
    self->decoder = NULL;
    self->frequency = 0;
    self->position = 0.0;

    self->channels = 2;
    self->bitrate = 0.0;
    self->samples = 0;
    self->frames = 0;
    self->profile = 0;
    self->profile_name = NULL;
    self->gain_radio = self->gain_audiophile = 0;
    self->peak_radio = self->peak_audiophile = 0;

    self->encoder_version = -1;
    self->encoder = NULL;
  }
  
  return (PyObject *)self;
}

static int MPCFile_init(MPCFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"filename", NULL}, *filename;
  mpc_streaminfo info;
  FILE *f;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &filename))
    return -1;
  
  if (!(self->reader = (mpc_reader_file *)malloc(sizeof(mpc_reader_file)))) {
    PyErr_SetString(PyExc_MemoryError, "unable to allocate reader");
    return -1;
  } else {
    self->reader->file = NULL;
  }

  f = fopen(filename, "r");
  if (f == NULL) {
    PyErr_SetFromErrno(PyExc_OSError);
    return -1;
  }
  mpc_reader_setup_file_reader(self->reader, f);

  if (mpc_streaminfo_read(&info, &(self->reader->reader)) != ERROR_CODE_OK) {
    PyErr_SetString(PyExc_IOError, "not a valid musepack file");
    return -1;
  }

  if (!(self->decoder = malloc(sizeof(mpc_decoder)))) {
    PyErr_SetString(PyExc_MemoryError, "unable to allocate decoder");
    return -1;
  }

  mpc_decoder_setup(self->decoder, &(self->reader->reader));
  if (!mpc_decoder_initialize(self->decoder, &info)) {
    PyErr_SetString(PyExc_IOError, "error initializing decoder");
    return -1;
  }

  self->frequency = info.sample_freq;
  self->channels = info.channels;
  self->frames = info.frames;
  self->channels = info.channels;
  self->bitrate = info.average_bitrate;
  self->samples = info.pcm_samples;

  self->stream_version = info.stream_version;
  self->encoder_version = info.encoder_version;
  self->encoder = strdup(info.encoder);
  self->profile = info.profile;
  self->profile_name = strdup(info.profile_name);

  self->gain_radio = info.gain_title;
  self->gain_audiophile = info.gain_album;
  self->peak_radio = info.peak_title;
  self->peak_audiophile = info.peak_album;

  self->length = (int)(mpc_streaminfo_get_length(&info) * 1000);
  return 0;
}

static void MPCFile_dealloc(MPCFile *self) {
  if (self == NULL) return;
  if (self->decoder) free(self->decoder);
  if (self->reader->file) fclose(self->reader->file);
  if (self->reader) free(self->reader);
  if (self->encoder) free(self->encoder);
  if (self->profile_name) free(self->profile_name);
  self->ob_type->tp_free((PyObject*)self);
}

static PyMemberDef MPCFile_members[] = {
    {"frequency", T_INT, offsetof(MPCFile, frequency), 0,
     "the sample frequency in Hz"},
    {"channels", T_INT, offsetof(MPCFile, channels), 0,
     "number of channels in the file (1 or 2)"},
    {"frames", T_UINT, offsetof(MPCFile, frames), 0,
     "number of channels in the file"},
    {"samples", T_UINT, offsetof(MPCFile, samples), 0,
     "number of samples in the file"},
    {"bitrate", T_DOUBLE, offsetof(MPCFile, bitrate), 0,
     "average bitrate of the file"},

    {"stream_version", T_INT, offsetof(MPCFile, stream_version), 0,
     "Musepack stream version number"},
    {"encoder_version", T_INT, offsetof(MPCFile, encoder_version), 0,
     "audio encoder version number"},
    {"encoder", T_STRING, offsetof(MPCFile, encoder), 0,
     "audio encoder identifier string"},

    {"profile", T_INT, offsetof(MPCFile, profile), 0,
     "audio encoding profile ('quality')"},
    {"profile_name", T_STRING, offsetof(MPCFile, profile_name), 0,
     "audio encoding profile name, in English"},

    {"gain_radio", T_INT, offsetof(MPCFile, gain_radio), 0,
     "ReplayGain 'radio' (per-track) volume adjustment"},
    {"gain_audiophile", T_INT, offsetof(MPCFile, gain_audiophile), 0,
     "ReplayGain 'audiophile' (per-album) volume adjustment"},
    {"peak_radio", T_UINT, offsetof(MPCFile, peak_radio), 0,
     "track volume peak"},
    {"peak_audiophile", T_UINT, offsetof(MPCFile, peak_audiophile), 0,
     "album volume peak"},

    {"length", T_UINT, offsetof(MPCFile, length), 0,
     "the song length in milliseconds"},
    {"position", T_DOUBLE, offsetof(MPCFile, position), 0,
     "the song position in milliseconds (a floating-point number)"},
    {NULL}
};

#ifdef MPC_FIXED_POINT
static int shift_signed(MPC_SAMPLE_FORMAT val, int shift) {
  if (shift > 0) val <<= shift;
  else if (shift < 0) val >>= -shift;
  return (int)val;
}
#endif

/* convert the MPC sample format (which are doubles) to a C string
   such as Python expects for its constructor. */
static void mpc_to_str(MPC_SAMPLE_FORMAT *from, char* to, unsigned int st) {
  unsigned int m_bps = 16;
  unsigned n;
  int float_scale = 1 << (m_bps - 1);
  int clip_min = -float_scale, clip_max = float_scale - 1;

  for (n = 0; n < 2 * st; n++) {
    int val;
#ifdef MPC_FIXED_POINT
    val = shift_signed(from[n], m_bps - MPC_FIXED_POINT_SCALE_SHIFT);
#else
    val = (int)(from[n] * float_scale);
#endif
    if (val < clip_min) val = clip_min;
    else if (val > clip_max) val = clip_max;
    unsigned int shift = 0;
    do {
      to[n * 2 + (shift / 8)] = (unsigned char)((val >> shift) & 0xFF);
      shift += 8;
    } while (shift < m_bps);
  }
}

static PyObject *MPCFile_read(MPCFile *self, PyObject *args, PyObject *kwds) {
  MPC_SAMPLE_FORMAT buffer[MPC_DECODER_BUFFER_LENGTH];

  int status = mpc_decoder_decode(self->decoder, buffer, 0, 0);
  /* status is the number of samples, -1 for error, 0 for EOF */

  if (status == -1) {
    PyErr_SetString(PyExc_IOError, "unable to read from file");
    return NULL;
  } else if (status == 0) {
    return Py_BuildValue("s", "");
  } else {
    int len = status * 4;
    char *sbuffer = malloc(len);
    mpc_to_str(buffer, sbuffer, status);
    PyObject *p = Py_BuildValue("s#", sbuffer, len);
    self->position += 1000 * ((double)status / (double)self->frequency);
    free(sbuffer);
    return p;
  }
}

static PyObject *MPCFile_seek(MPCFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"position", NULL};
  int ms = -1;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "i", kwlist, &ms))
    return NULL;
  if (ms <= self->length) {
    mpc_int64_t sample = (mpc_int64_t)((ms/1000.0) * self->frequency);
    mpc_decoder_seek_sample(self->decoder, sample);
    self->position = ms;
    return Py_BuildValue("");
  } else {
    PyErr_SetString(PyExc_IOError, "attempt to seek past end of file");
    return NULL;
  }
}

static PyObject *MPCFile_scale(MPCFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"scale", NULL};
  double scale = 1.0;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "d", kwlist, &scale))
    return NULL;
  if (scale < 0.0) {
    PyErr_SetString(PyExc_ValueError, "scale must be at least 0");
    return NULL;
  } else {
    mpc_decoder_scale_output(self->decoder, scale);
    return Py_BuildValue("");
  }
}

static PyMethodDef MPCFile_methods[] = {
  {"read", (PyCFunction)MPCFile_read, METH_NOARGS,
   "Return stereo audio data in a Python string. If\n\
    you are at the end of the file, an empty string will\n\
    be returned."
    },
  {"seek", (PyCFunction)MPCFile_seek, METH_KEYWORDS,
   "Seek to the specified position (in milliseconds).\n\
    An IOError will be thrown if you attempt to seek past\n\
    the end of the file."
    },
  {"set_scale", (PyCFunction)MPCFile_scale, METH_KEYWORDS,
   "Scale decoded audio output.\n\
    All decoded samples will be multiplied by this scale factor."
    },
    {NULL}
};

static PyTypeObject MPCFileType = {
  PyObject_HEAD_INIT(NULL)
  0,                         /*ob_size*/
  "musepack.mpc.MPCFile",    /*tp_name*/
  sizeof(MPCFile),           /*tp_basicsize*/
  0,                         /*tp_itemsize*/
  (destructor)MPCFile_dealloc, /*tp_dealloc*/
  0,                         /*tp_print*/
  0,                         /*tp_getattr*/
  0,                         /*tp_setattr*/
  0,                         /*tp_compare*/
  0,                         /*tp_repr*/
  0,                         /*tp_as_number*/
  0,                         /*tp_as_sequence*/
  0,                         /*tp_as_mapping*/
  0,                         /*tp_hash */
  0,                         /*tp_call*/
  0,                         /*tp_str*/
  0,                         /*tp_getattro*/
  0,                         /*tp_setattro*/
  0,                         /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
  "MPCFile objects - a loaded audio file",
  0,		               /* tp_traverse */
  0,		               /* tp_clear */
  0,		               /* tp_richcompare */
  0,		               /* tp_weaklistoffset */
  0,		               /* tp_iter */
  0,		               /* tp_iternext */
  MPCFile_methods,             /* tp_methods */
  MPCFile_members,             /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)MPCFile_init,      /* tp_init */
  0,                         /* tp_alloc */
  MPCFile_new,                 /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}
};

#ifndef PyMPCINIT_FUNC
#define PyMPCINIT_FUNC void
#endif
PyMODINIT_FUNC initmpc(void) 
{
    PyObject* m;

    if (PyType_Ready(&MPCFileType) < 0) return;

    m = Py_InitModule3("mpc", module_methods,
                       "An interface to libmusepack, an MPC decoder");

    if (m == NULL) return;

    Py_INCREF(&MPCFileType);
    PyModule_AddObject(m, "MPCFile", (PyObject *)&MPCFileType);
}
