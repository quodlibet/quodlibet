/* A simple wrapper for FAAD2 metadata interface. It also provides
   information about audio track length, average bitrate and
   frequency.
   Uses FAAD2, http://www.audiocoding.com/
   Partly based on the code from faad2/plugins/foo_mp4/foo_mp4.cpp
   Copyright 2005 Alexey Bobyakov

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License version 2 as
   published by the Free Software Foundation.
*/

#include <Python.h>
#include <structmember.h>
#include <mp4.h>
#include <faad.h>

int
GetAACTrack(MP4FileHandle infile)
{
    /* find AAC track */
    int i, rc;
    int numTracks = MP4GetNumberOfTracks(infile, NULL, 0);

    for (i = 0; i < numTracks; i++) {
        MP4TrackId trackId = MP4FindTrackId(infile, i, NULL, 0);
        const char *trackType = MP4GetTrackType(infile, trackId);

        if (!strcmp(trackType, MP4_AUDIO_TRACK_TYPE)) {
            unsigned char *buff = NULL;
            int buff_size = 0;
            mp4AudioSpecificConfig mp4ASC;

            MP4GetTrackESConfiguration(infile, trackId, &buff,
                                       &buff_size);

            if (buff) {
                rc = AudioSpecificConfig(buff, buff_size, &mp4ASC);
                free(buff);

                if (rc < 0) {
                    return -1;
                }
                return trackId;
            }
        }
    }

    /* can't decode this */
    return -1;
}

typedef struct
{
    PyObject_HEAD
    MP4FileHandle file;
    char *filename;

    unsigned int length;
    int frequency;
    double bitrate;
} MP4File;

static PyObject *
MP4File_new(PyTypeObject * type, PyObject * args, PyObject * kwds)
{
    MP4File *self;

    self = (MP4File *) type->tp_alloc(type, 0);
    if (self != NULL) {
        self->file = 0;
        self->length = 0;
        self->bitrate = 0.0;
        self->frequency = 0;
        self->filename = NULL;
    }

    return (PyObject *) self;
}

static int
MP4File_init(MP4File * self, PyObject * args, PyObject * kwds)
{
    static char *kwlist[] = { "filename", "modify", NULL };
    char *filename, modify = 0;
    unsigned char *config = NULL;
    int track;
    MP4Duration duration;

    if (!PyArg_ParseTupleAndKeywords
        (args, kwds, "s|b", kwlist, &filename, &modify)) {
        return -1;
    }
    
    self->file = MP4Read(filename, 0);
    if (!self->file) {
        PyErr_SetString(PyExc_IOError, "not a valid MP4 file");
        return -1;
    }

    if ((track = GetAACTrack(self->file)) < 0) {
        MP4Close(self->file);
        PyErr_SetString(PyExc_IOError,
                        "the file doesn't contain AAC track");
        return -1;
    }

    self->frequency = MP4GetTrackTimeScale(self->file, track);
    duration = MP4GetTrackDuration(self->file, track);
    self->length =
        (unsigned int) MP4ConvertFromTrackDuration(self->file, track,
                                                   duration,
                                                   MP4_MSECS_TIME_SCALE);

    self->bitrate = (double) (MP4GetTrackBitRate(self->file, track) + 500);
    self->filename = strdup(filename);
    if (modify) {
        MP4Close(self->file);
        self->file = MP4Modify(filename, 0, 0);
        if (self->file == MP4_INVALID_FILE_HANDLE) {
            PyErr_SetString(PyExc_IOError, "not a valid MP4 file");
            return -1;
        }
    }

    return 0;
}

static void
MP4File_dealloc(MP4File * self)
{
    if (self == NULL) {
        return;
    }
    if (self->filename) {
        free(self->filename);
    }
    MP4Close(self->file);
    self->ob_type->tp_free((PyObject *) self);
}

static PyObject *
MP4File_deleteAllTags(MP4File * self, PyObject * args)
{
    MP4Close(self->file);
    self->file = MP4Modify(self->filename, 0, 0);
    if (self->file == MP4_INVALID_FILE_HANDLE) {
        PyErr_SetString(PyExc_IOError, "deleteAllTags: not a valid MP4 file #1");
        return NULL;
    }
    MP4MetadataDelete(self->file);
    MP4Close(self->file);

//    MP4Optimize(self->filename, NULL, 0);

    self->file = MP4Modify(self->filename, 0, 0);
    if (self->file == MP4_INVALID_FILE_HANDLE) {
        PyErr_SetString(PyExc_IOError, "deleteAllTags: not a valid MP4 file #2");
        return NULL;
    }
    return Py_BuildValue("");
}

static PyObject *
MP4File_setTag(MP4File * self, PyObject * args, PyObject * kwds)
{
    static char *kwlist[] = { "key", "value", NULL };
    char *key, *value, kind;
    int size;

    if (!PyArg_ParseTupleAndKeywords
        (args, kwds, "ss#", kwlist, &key, &value, &size)) {
        return NULL;
    }

    if (strcasecmp(key, "©nam") == 0) {
        MP4SetMetadataName(self->file, value);
    } else if (strcasecmp(key, "©ART") == 0) {
        MP4SetMetadataArtist(self->file, value);
    } else if (strcasecmp(key, "©wrt") == 0) {
        MP4SetMetadataWriter(self->file, value);
    } else if (strcasecmp(key, "©alb") == 0) {
        MP4SetMetadataAlbum(self->file, value);
    } else if (strcasecmp(key, "©day") == 0) {
        MP4SetMetadataYear(self->file, value);
    } else if (strcasecmp(key, "©cmt") == 0) {
        MP4SetMetadataComment(self->file, value);
    } else if (strcasecmp(key, "©gen") == 0) {
        MP4SetMetadataGenre(self->file, value);
    } else if (strcasecmp(key, "trkn") == 0) {
        char *p = strchr(value, '/');
        u_int16_t trkn = 0, tot = 0;
        if (!p) {
            trkn = atoi(value);
        } else {
            *p = 0;
            trkn = atoi(value);
            tot = atoi(++p);
        }
        MP4SetMetadataTrack(self->file, trkn, tot);
    } else if (strcasecmp(key, "disk") == 0) {
        char *p = strchr(value, '/');
        u_int16_t disk = 0, tot = 0;
        if (!p) {
            disk = atoi(value);
        } else {
            *p = 0;
            disk = atoi(value);
            tot = atoi(++p);
        }
        MP4SetMetadataDisk(self->file, disk, tot);
    } else if (strcasecmp(key, "cpil") == 0) {
        u_int8_t cpil = atoi(value);
        MP4SetMetadataCompilation(self->file, cpil);
    } else if (strcasecmp(key, "tmpo") == 0) {
        u_int16_t tempo = atoi(value);
        MP4SetMetadataTempo(self->file, tempo);
    } else if (strcasecmp(key, "covr") == 0) {
        MP4SetMetadataCoverArt(self->file, (u_int8_t *) value, size);
    } else {
        MP4SetMetadataFreeForm(self->file, key, (u_int8_t *) value,
                               size);
    }

    return Py_BuildValue("");
}

static PyMemberDef MP4File_members[] = {
    {"length", T_INT, offsetof(MP4File, length), 0,
     "the song length in milliseconds"},
    {"bitrate", T_DOUBLE, offsetof(MP4File, bitrate), 0,
     "average bitrate of the file"},
    {"frequency", T_INT, offsetof(MP4File, frequency), 0,
     "the sample frequency in Hz"},
    {NULL}
};


static PyMethodDef MP4File_methods[] = {
    {"setTag", (PyCFunction) MP4File_setTag, METH_KEYWORDS,
     "Sets tag with 'key' to 'value'"},
    {"deleteAllTags", (PyCFunction) MP4File_deleteAllTags, METH_NOARGS,
     "Deletes all tags in the file"},
    {NULL}
};

static PyTypeObject MP4FileType = {
    PyObject_HEAD_INIT(NULL)
        0,                      /*ob_size */
    "mp4info.mp4.MP4File",      /*tp_name */
    sizeof(MP4File),            /*tp_basicsize */
    0,                          /*tp_itemsize */
    (destructor) MP4File_dealloc,       /*tp_dealloc */
    0,                          /*tp_print */
    0,                          /*tp_getattr */
    0,                          /*tp_setattr */
    0,                          /*tp_compare */
    0,                          /*tp_repr */
    0,                          /*tp_as_number */
    0,                          /*tp_as_sequence */
    0,                          /*tp_as_mapping */
    0,                          /*tp_hash */
    0,                          /*tp_call */
    0,                          /*tp_str */
    0,                          /*tp_getattro */
    0,                          /*tp_setattro */
    0,                          /*tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,   /*tp_flags */
    "MP4 objects.",
    0,                          /* tp_traverse */
    0,                          /* tp_clear */
    0,                          /* tp_richcompare */
    0,                          /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    MP4File_methods,            /* tp_methods */
    MP4File_members,            /* tp_members */
    0,                          /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    (initproc) MP4File_init,    /* tp_init */
    0,                          /* tp_alloc */
    MP4File_new,                /* tp_new */
};

static PyMethodDef module_methods[] = {
    {NULL}
};

#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initmp4(void)
{
    PyObject *m;

    if (PyType_Ready(&MP4FileType) < 0) {
        return;
    }

    m = Py_InitModule3("mp4", module_methods,
                       "A simple wrapper for FAAD2 metadata interface");

    if (m == NULL) {
        return;
    }

    Py_INCREF(&MP4FileType);
    PyModule_AddObject(m, "MP4File", (PyObject *) & MP4FileType);
}
