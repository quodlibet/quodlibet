/* include this first, before NO_IMPORT_PYGOBJECT is defined */
#include <pygobject.h>

void statusicon_register_classes (PyObject *d);

extern PyMethodDef statusicon_functions[];

DL_EXPORT(void)
initstatusicon(void)
{
    PyObject *m, *d;
	
    init_pygobject ();

    m = Py_InitModule ("statusicon", statusicon_functions);
    d = PyModule_GetDict (m);
	
    statusicon_register_classes (d);

    if (PyErr_Occurred ()) {
	Py_FatalError ("can't initialise module statusicon");
    }
}
