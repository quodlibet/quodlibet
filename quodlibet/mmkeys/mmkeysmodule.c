/* Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL. */

#include <pygobject.h>

void mmkeys_register_classes(PyObject *d);

extern PyMethodDef mmkeys_functions[];

DL_EXPORT(void) initmmkeys(void) {
    PyObject *m, *d;
	
    init_pygobject();

    m = Py_InitModule("mmkeys", mmkeys_functions);
    d = PyModule_GetDict(m);
	
    mmkeys_register_classes(d);

    if (PyErr_Occurred()) Py_FatalError("can't initialise module mmkeys");
}
