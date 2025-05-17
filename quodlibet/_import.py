# Copyright 2017 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import importlib
import importlib.util


class RedirectImportHook:
    """Import hook which loads packages as sub packages.

    e.g. "import raven" will import "quodlibet.packages.raven" even
    if raven uses absolute imports internally.
    """

    def __init__(self, name, packages):
        """
        Args:
            name (str): The package path to load the packages from
            packages (List[str]): A list of packages provided
        """

        for package in packages:
            if package in sys.modules:
                raise Exception(f"{package!r} already loaded, can't redirect")

        self._name = name
        self._packages = packages

    def find_spec(self, fullname, path, target=None):
        loader = self.find_module(fullname, path)
        if loader is not None:
            return importlib.util.spec_from_loader(fullname, loader)
        return None

    def find_module(self, fullname, path=None):
        package = fullname.split(".")[0]
        if package in self._packages:
            return self
        return None

    def load_module(self, name):
        mod = None
        if name in sys.modules:
            mod = sys.modules[name]
        loadname = self._name + "." + name
        if loadname in sys.modules:
            mod = sys.modules[loadname]
        if mod is None:
            mod = importlib.import_module(loadname)
        sys.modules[name] = mod
        sys.modules[loadname] = mod
        return mod


def install_redirect_import_hook():
    """Install the import hook, does not import anything"""

    import_hook = RedirectImportHook("quodlibet.packages", ["senf", "raven"])
    sys.meta_path.insert(0, import_hook)
