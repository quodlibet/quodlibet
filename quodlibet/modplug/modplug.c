/* Copyright 2004 Joe Wreschnig. Licensed under the GNU GPL version 2. */
#include <Python.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <string.h>
#include <fcntl.h>
#include <libmodplug/modplug.h>
#include <structmember.h>

static ModPlug_Settings settings;

#define MF_SAMPLE_RATE 44100
#define MF_CHANNELS 2
#define MF_BITS_PER_CHANNEL 16

typedef struct {
  PyObject_HEAD
  ModPlugFile *mf;
  int length;
  double position;
  void *mem;
  const char *title, *filename;
} ModFile;

static PyObject
*ModFile_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
  ModFile *self;

  self = (ModFile *)type->tp_alloc(type, 0);
  if (self != NULL) {
    self->mf = NULL;
    self->length = self->position = 0;
    self->mem = NULL;
    self->title = self->filename = NULL;
  }
  
  return (PyObject *)self;
}

static int ModFile_init(ModFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"filename", NULL}, *filename;
  struct stat st;
  int fd, size;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "s", kwlist, &filename))
    return -1;
  
  if (stat(filename, &st) != 0) return -1;
  size = st.st_size;

  fd = open(filename, O_RDONLY);
  if (fd == -1) return -1;

  self->mem = (void *)malloc(size);
  read(fd, self->mem, size);

  self->mf = ModPlug_Load(self->mem, size);

  self->title = ModPlug_GetName(self->mf);
  self->length = ModPlug_GetLength(self->mf);
  self->filename = strdup(filename);

  /* if no title is available, use the filename */
  if (!strcmp(self->title, "")) self->title = basename(self->filename);

  close(fd);
  return 0;
}

static void ModFile_dealloc(ModFile *self) {
  ModPlug_Unload(self->mf);
  free(self->mem);
  free(self->filename);
  self->ob_type->tp_free((PyObject*)self);
}

static PyMemberDef ModFile_members[] = {
    {"title", T_STRING, offsetof(ModFile, title), 0, "song title"},
    {"length", T_INT, offsetof(ModFile, length), 0, "song length in ms"},
    {"position", T_DOUBLE, offsetof(ModFile, position), 0,
     "current position in ms"},
    {NULL}
};

static PyObject *ModFile_read(ModFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"size", NULL};
  int buffer_size, buffer_len;
  char *buffer;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "i", kwlist, &buffer_size))
    return -1;

  buffer = (char *)malloc(buffer_size);
  buffer_len = ModPlug_Read(self->mf, buffer, buffer_size);
  if (buffer_len == 0) {
    /* FIXME: Raise EOF exception of some sort */
    free(buffer);
    return Py_BuildValue("s", "");
  } else {
    PyObject *p = Py_BuildValue("s#", buffer, buffer_len);
    /* 1 / 176.4 = 1000 / 2 / 2 / 44100 */
    self->position += buffer_len / 176.4;
    free(buffer);
    return p;
  }
}

static PyObject *ModFile_seek(ModFile *self, PyObject *args, PyObject *kwds) {
  static char *kwlist[] = {"position", NULL};
  int ms;
  if (!PyArg_ParseTupleAndKeywords(args, kwds, "i", kwlist, &ms))
    return -1;
  ModPlug_Seek(self->mf, ms);
  self->position = ms;
  return Py_BuildValue("");
}


static PyMethodDef ModFile_methods[] = {
  {"read", (PyCFunction)ModFile_read, METH_KEYWORDS,
     "Return audio data of no more than the given length."
    },
  {"seek", (PyCFunction)ModFile_seek, METH_KEYWORDS,
     "Seek to the specified position (in milliseconds)."
    },
    {NULL}
};


static PyTypeObject ModFileType = {
  PyObject_HEAD_INIT(NULL)
  0,                         /*ob_size*/
  "modplug.ModFile",         /*tp_name*/
  sizeof(ModFile),           /*tp_basicsize*/
  0,                         /*tp_itemsize*/
  (destructor)ModFile_dealloc, /*tp_dealloc*/
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
  "ModFile objects",         /* tp_doc */
  0,		               /* tp_traverse */
  0,		               /* tp_clear */
  0,		               /* tp_richcompare */
  0,		               /* tp_weaklistoffset */
  0,		               /* tp_iter */
  0,		               /* tp_iternext */
  ModFile_methods,             /* tp_methods */
  ModFile_members,             /* tp_members */
  0,                         /* tp_getset */
  0,                         /* tp_base */
  0,                         /* tp_dict */
  0,                         /* tp_descr_get */
  0,                         /* tp_descr_set */
  0,                         /* tp_dictoffset */
  (initproc)ModFile_init,      /* tp_init */
  0,                         /* tp_alloc */
  ModFile_new,                 /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}
};

#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC initmodplug(void) 
{
    PyObject* m;

    if (PyType_Ready(&ModFileType) < 0) return;

    m = Py_InitModule3("modplug", module_methods,
                       "An interface to libmodplug, a MOD decoder.");

    if (m == NULL) return;

    Py_INCREF(&ModFileType);
    PyModule_AddObject(m, "ModFile", (PyObject *)&ModFileType);
    ModPlug_GetSettings(&settings);
    settings.mLoopCount = 0;
    settings.mChannels = MF_CHANNELS;
    settings.mBits = MF_BITS_PER_CHANNEL;
    settings.mFrequency = MF_SAMPLE_RATE;
    settings.mFlags = (MODPLUG_ENABLE_OVERSAMPLING |
		       MODPLUG_ENABLE_NOISE_REDUCTION);
    settings.mResamplingMode = MODPLUG_RESAMPLE_FIR;
    ModPlug_SetSettings(&settings);
}
