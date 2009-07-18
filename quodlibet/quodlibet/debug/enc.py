# This is totally a giant hack.
# A totally awesome giant hack.
# When it works.
# Someone should make it better.

# Code originally by Knio from #pygame.

import os
import gc
import sys
import types

import quodlibet.const as const
import quodlibet.util as util

def __reloadmodule(module, reload=reload):
    old = {}
    old.update(module.__dict__)
    reload(module)
    new = module.__dict__
    
    for key in old:
        oldvalue = old[key]
        newvalue = new[key]
        
        if oldvalue is newvalue:
            continue
        
        refs = gc.get_referrers(oldvalue)
        for ref in refs:
            if ref is old:
                continue
        refs = gc.get_referrers(oldvalue)
        for ref in refs:
            if ref is old:
                continue
                    
            if type(ref) == types.InstanceType:
                if ref.__class__ is oldvalue:
                    ref.__class__ = newvalue
                    
            if type(ref) == types.DictType:
                for i in ref:
                    if ref[i] is oldvalue:
                        ref[i] = newvalue

            if type(ref) == types.ListType:
                try:
                    while True:
                        ref[ref.index(oldvalue)] = newvalue
                except ValueError:
                    pass

def reload():
    for name, module in sys.modules.items():
        if name == '__main__' or module == None:
            continue

        if name.startswith("quodlibet."):
            name = name.replace(".", os.sep)
            filename = os.path.join(const.BASEDIR, name[name.find(os.sep)+1:])
            py = filename + ".py"
            pyc = filename + ".pyc"
            if util.mtime(pyc) and util.mtime(pyc) < util.mtime(py):
                try: __reloadmodule(module)
                except ImportError: pass
                else: print_d("Reloading %s" % name)
