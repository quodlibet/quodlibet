/* Copyright 2004 Joe Wreschnig. Released under the terms of the GNU GPL. */

#include <pygobject.h>

void _mmkeys_register_classes(PyObject *d);

extern PyMethodDef _mmkeys_functions[];

DL_EXPORT(void) init_mmkeys(void) {
    PyObject *m, *d;
	
    init_pygobject();

    m = Py_InitModule("_mmkeys", _mmkeys_functions);
    d = PyModule_GetDict(m);
	
    _mmkeys_register_classes(d);

    if (PyErr_Occurred()) Py_FatalError("can't initialise module mmkeys");
}
