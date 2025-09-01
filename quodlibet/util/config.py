# Copyright 2004-2008 Joe Wreschnig
#           2009-2025 Nick Boultbee
#           2011-2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Simple proxy to a Python ConfigParser

ConfigParser uses "str" on both Python 2/3, on Python 2 we simply encode
text/windows paths using utf-8 and save bytes as is.

On Python 3 we save text as is, convert paths to bytes/utf-8 and convert bytes
to unicode with utf-8/surrogateescape.

The final representation on disk should then in both cases be the same.
"""

import collections
import csv
import os
from configparser import Error, NoSectionError
from configparser import RawConfigParser as ConfigParser
from io import StringIO
from typing import Any, cast
from collections.abc import Callable

from senf import fsnative

from quodlibet import print_w
from quodlibet.util import list_unique, print_d
from quodlibet.util.atomic import atomic_save
from quodlibet.util.path import mkdir
from quodlibet.util.string import join_escape, split_escape


# In newer RawConfigParser it is possible to replace the internal dict. The
# implementation only uses items() for writing, so replace with a dict that
# returns them sorted. This makes it easier to look up entries in the file.
class _sorted_dict(collections.OrderedDict):  # noqa
    def items(self):
        return sorted(super().items())


class _Default:
    pass


_DEFAULT: _Default = _Default()

UpgradeFunction = Callable[["Config", int, int], None]
"""function(config, old_version: int, new_version: int) -> None"""


class Config:
    """A wrapper around RawConfigParser.

    Provides a ``defaults`` attribute of the same type which can be used
    to set default values.
    """

    def __init__(self, version: int | None = None, _defaults: bool = True):
        """Use read() to read in an existing config file.

        version should be an int starting with 0 that gets incremented if you
        want to register a new upgrade function. If None, upgrade is disabled.
        """

        self._config = ConfigParser(dict_type=_sorted_dict)
        self.defaults = None
        if _defaults:
            self.defaults = Config(_defaults=False)
        self._version = version
        self._loaded_version: int | None = None
        self._upgrade_funcs: list[UpgradeFunction] = []

    def _do_upgrade(self, func: UpgradeFunction) -> None:
        assert self._loaded_version is not None
        assert self._version is not None

        old_version = self._loaded_version
        new_version = self._version
        if old_version != new_version:
            print_d("Config upgrade: %d->%d (%r)" % (old_version, new_version, func))
            func(self, old_version, new_version)

    def get_version(self) -> int:
        """Get the version of the loaded config file (for testing only)

        Raises Error if no file was loaded or versioning is disabled.
        """

        if self._version is None:
            raise Error("Versioning disabled")

        if self._loaded_version is None:
            raise Error("No file loaded")

        return self._loaded_version

    def register_upgrade_function(self, function: UpgradeFunction) -> UpgradeFunction:
        """Register an upgrade function that gets called at each read()
        if the current config version and the loaded version don't match.

        Can also be registered after read was called.
        """

        if self._version is None:
            raise Error("Versioning disabled")

        self._upgrade_funcs.append(function)
        # after read(), so upgrade now
        if self._loaded_version is not None:
            self._do_upgrade(function)
        return function

    def reset(self, section: str, option: str) -> None:
        """Reset the value to the default state"""

        assert self.defaults is not None

        try:
            self._config.remove_option(section, option)
        except NoSectionError:
            pass

    def options(self, section: str) -> list[str]:
        """Returns a list of options available in the specified section."""

        try:
            options = self._config.options(section)
        except NoSectionError:
            if self.defaults:
                return self.defaults.options(section)
            raise
        else:
            if self.defaults:
                try:
                    options.extend(self.defaults.options(section))
                    options = list_unique(options)
                except NoSectionError:
                    pass
            return options

    def get(self, section: str, option: str, default: str | _Default = _DEFAULT) -> str:
        """
        If default is not given or set, raises Error in case of an error
        """

        try:
            return self._config.get(section, option)
        except Error as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.get(section, option)
                    except Error:
                        pass
                raise
            if "No section:" in str(e):
                print_w(f"Config problem: {e}")
            return cast(str, default)

    def gettext(self, *args, **kwargs):
        value = self.get(*args, **kwargs)
        # make sure there are no surrogates
        value.encode("utf-8")
        return value

    def getbytes(
        self, section: str, option: str, default: bytes | _Default = _DEFAULT
    ) -> bytes:
        try:
            value = self._config.get(section, option)
            return value.encode("utf-8", "surrogateescape")
        except (Error, ValueError) as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getbytes(section, option)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(bytes, default)

    def getboolean(
        self, section: str, option: str, default: bool | _Default = _DEFAULT
    ) -> bool:
        """If default is not given or set, raises Error in case of an error"""

        try:
            return self._config.getboolean(section, option)
        except (Error, ValueError) as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getboolean(section, option)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(bool, default)

    def getint(
        self, section: str, option: str, default: int | _Default = _DEFAULT
    ) -> int:
        """
        If default is not given or set, raises Error in case of an error
        """

        try:
            return int(self._config.getfloat(section, option))
        except (Error, ValueError) as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getint(section, option)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(int, default)

    def getfloat(
        self, section: str, option: str, default: float | _Default = _DEFAULT
    ) -> float:
        """If default is not given or set, raises Error in case of an error"""

        try:
            return self._config.getfloat(section, option)
        except (Error, ValueError) as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getfloat(section, option)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(float, default)

    def getstringlist(
        self, section: str, option: str, default: list[str] | _Default = _DEFAULT
    ) -> list[str]:
        """
        If default is not given or set, raises Error in case of an error.
        Gets a list of strings, using CSV to parse and delimit.
        """

        try:
            value = self._config.get(section, option)

            parser = csv.reader([value], lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
            try:
                vals = next(parser)
            except (csv.Error, ValueError) as e:
                raise Error(str(e)) from e
            return vals
        except Error as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getstringlist(section, option)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(list[str], default)

    def setstringlist(self, section: str, option: str, values: list[str]) -> None:
        """Saves a list of Unicode strings using the csv module"""

        sw = StringIO()
        values = [str(v) for v in values]

        writer = csv.writer(sw, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(values)
        self.set(section, option, sw.getvalue())

    def setlist(self, section: str, option: str, values: list[str], sep=",") -> None:
        """Saves a list of str using ',' as a separator and \\ for escaping"""

        values = [str(v) for v in values]
        joined = join_escape(values, sep)
        self.set(section, option, joined)

    def getlist(
        self,
        section: str,
        option: str,
        default: list[str] | _Default = _DEFAULT,
        sep=",",
    ) -> list[str]:
        """Returns a str list saved with setlist()"""

        try:
            value = self._config.get(section, option)
            return split_escape(value, sep)
        except (Error, ValueError) as e:
            if default is _DEFAULT:
                if self.defaults is not None:
                    try:
                        return self.defaults.getlist(section, option, sep=sep)
                    except Error:
                        pass
                raise Error(str(e)) from e
            return cast(list[str], default)

    def set(self, section: str, option: str, value: Any) -> None:
        """Saves the string representation for the passed value

        Don't pass unicode, encode first.
        """

        if isinstance(value, bytes):
            raise TypeError("use setbytes")

        # RawConfigParser only allows string values but doesn't
        # scream if they are not (and it only fails before the
        # first config save...)
        if not isinstance(value, str):
            value = str(value)

        try:
            self._config.set(section, option, value)
        except NoSectionError:
            if self.defaults and self.defaults.has_section(section):
                self._config.add_section(section)
                self._config.set(section, option, value)
            else:
                raise

    def settext(self, section: str, option: str, value: Any) -> None:
        value = str(value)

        # make sure there are no surrogates
        value.encode("utf-8")

        self.set(section, option, value)

    def setbytes(self, section: str, option: str, value: bytes) -> None:
        assert isinstance(value, bytes)

        str_value = value.decode("utf-8", "surrogateescape")

        self.set(section, option, str_value)

    def write(self, filename: fsnative) -> None:
        """Write config to filename.

        :raises EnvironmentError: When writing the file fails.
        """

        assert isinstance(filename, fsnative)

        mkdir(os.path.dirname(filename))

        # Temporarily set the new version for saving
        if self._version is not None:
            self.add_section("__config__")
            self.set("__config__", "version", self._version)
        try:
            with atomic_save(filename, "wb") as fileobj:
                temp = StringIO()
                self._config.write(temp)
                data = temp.getvalue().encode("utf-8", "surrogateescape")
                fileobj.write(data)
        finally:
            if self._loaded_version is not None:
                self.set("__config__", "version", self._loaded_version)

    def clear(self) -> None:
        """Remove all sections."""

        for section in self._config.sections():
            self._config.remove_section(section)

    def is_empty(self) -> bool:
        """Whether the config has any sections"""

        return not self._config.sections()

    def read(self, filename) -> None:
        """Reads the config from `filename` if the file exists,
        otherwise does nothing

        Can raise EnvironmentError, Error.
        """

        try:
            with open(filename, "rb") as fileobj:
                io = StringIO(fileobj.read().decode("utf-8", "surrogateescape"))
                self._config.read_file(io, filename)
        except OSError:
            print_d(f"No config file found at {filename} – using defaults")
            return

        # don't upgrade if we just created a new config
        if self._version is not None:
            self._loaded_version = self.getint("__config__", "version", -1)
            for func in self._upgrade_funcs:
                self._do_upgrade(func)

    def has_option(self, section: str, option: str) -> bool:
        """If the given section exists, and contains the given option"""

        return self._config.has_option(section, option) or (
            self.defaults is not None and self.defaults.has_option(section, option)
        )

    def has_section(self, section: str) -> bool:
        """If the given section exists"""

        return self._config.has_section(section) or (
            self.defaults is not None and self.defaults.has_section(section)
        )

    def remove_option(self, section: str, option: str) -> bool:
        """Remove the specified option from the specified section

        :raises Error: If the section or option doesn't exist.
        """

        return self._config.remove_option(section, option)

    def add_section(self, section: str) -> None:
        """Add a section to the instance if it doesn't already exist."""

        if not self._config.has_section(section):
            self._config.add_section(section)


class ConfigProxy:
    """Provides a Config object with a fixed section and a possibility to
    prefix option names in that section.

    e.g. it can create a view of the "plugin" section and prefix all
    options with a plugin name.
    """

    def __init__(self, real_config, section_name, _defaults=True):
        self._real_config = real_config
        self._section_name = section_name
        self.defaults = None
        if _defaults:
            self.defaults = self._new_defaults(real_config.defaults)

    def _new_defaults(self, real_default_config):
        return ConfigProxy(real_default_config, self._section_name, False)

    def _option(self, name: str) -> str:
        """Override if you want to change option names. e.g. prefix them"""

        return name

    @classmethod
    def _init_wrappers(cls) -> None:
        def get_func(name: str):
            def method(self, option, *args, **kwargs):
                config_getter = getattr(self._real_config, name)
                return config_getter(
                    self._section_name, self._option(option), *args, **kwargs
                )

            return method

        # methods starting with a section arg
        for name in [
            "get",
            "set",
            "getboolean",
            "getint",
            "getfloat",
            "reset",
            "settext",
            "gettext",
            "getbytes",
            "setbytes",
        ]:
            setattr(cls, name, get_func(name))


ConfigProxy._init_wrappers()
