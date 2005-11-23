/* Copyright 2004 Joe Wreschnig. Released under the terms of the GNU LGPL. */

#include <pygobject.h>

void trayicon_register_classes (PyObject *d);

extern PyMethodDef trayicon_functions[];

DL_EXPORT(void) init_trayicon(void) {
    PyObject *m, *d;
	
    init_pygobject();

    m = Py_InitModule("_trayicon", trayicon_functions);
    d = PyModule_GetDict(m);
	
    trayicon_register_classes(d);

    if (PyErr_Occurred()) Py_FatalError ("can't initialize module trayicon");
}
