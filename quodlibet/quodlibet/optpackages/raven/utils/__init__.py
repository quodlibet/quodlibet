"""
raven.utils
~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""
from __future__ import absolute_import

from raven.utils.compat import iteritems, string_types
import logging
import threading
from functools import update_wrapper
try:
    import pkg_resources
except ImportError:
    pkg_resources = None  # NOQA
import sys

logger = logging.getLogger('raven.errors')


def merge_dicts(*dicts):
    out = {}
    for d in dicts:
        if not d:
            continue

        for k, v in iteritems(d):
            out[k] = v
    return out


def varmap(func, var, context=None, name=None):
    """
    Executes ``func(key_name, value)`` on all values
    recurisively discovering dict and list scoped
    values.
    """
    if context is None:
        context = {}
    objid = id(var)
    if objid in context:
        return func(name, '<...>')
    context[objid] = 1
    if isinstance(var, dict):
        ret = dict((k, varmap(func, v, context, k))
                   for k, v in iteritems(var))
    elif isinstance(var, (list, tuple)):
        ret = [varmap(func, f, context, name) for f in var]
    else:
        ret = func(name, var)
    del context[objid]
    return ret


# We store a cache of module_name->version string to avoid
# continuous imports and lookups of modules
_VERSION_CACHE = {}


def get_version_from_app(module_name, app):
    version = None

    # Try to pull version from pkg_resource first
    # as it is able to detect version tagged with egg_info -b
    if pkg_resources is not None:
        # pull version from pkg_resources if distro exists
        try:
            return pkg_resources.get_distribution(module_name).version
        except Exception:
            pass

    if hasattr(app, 'get_version'):
        version = app.get_version
    elif hasattr(app, '__version__'):
        version = app.__version__
    elif hasattr(app, 'VERSION'):
        version = app.VERSION
    elif hasattr(app, 'version'):
        version = app.version

    if callable(version):
        version = version()

    if not isinstance(version, (string_types, list, tuple)):
        version = None

    if version is None:
        return None

    if isinstance(version, (list, tuple)):
        version = '.'.join(map(str, version))

    return str(version)


def get_versions(module_list=None):
    if not module_list:
        return {}

    ext_module_list = set()
    for m in module_list:
        parts = m.split('.')
        ext_module_list.update('.'.join(parts[:idx])
                               for idx in range(1, len(parts) + 1))

    versions = {}
    for module_name in ext_module_list:
        if module_name not in _VERSION_CACHE:
            try:
                __import__(module_name)
            except ImportError:
                continue

            try:
                app = sys.modules[module_name]
            except KeyError:
                continue

            try:
                version = get_version_from_app(module_name, app)
            except Exception as e:
                logger.exception(e)
                version = None

            _VERSION_CACHE[module_name] = version
        else:
            version = _VERSION_CACHE[module_name]
        if version is None:
            continue
        versions[module_name] = version
    return versions


def get_auth_header(protocol, timestamp, client, api_key,
                    api_secret=None, **kwargs):
    header = [
        ('sentry_timestamp', timestamp),
        ('sentry_client', client),
        ('sentry_version', protocol),
        ('sentry_key', api_key),
    ]
    if api_secret:
        header.append(('sentry_secret', api_secret))

    return 'Sentry %s' % ', '.join('%s=%s' % (k, v) for k, v in header)


class memoize(object):
    """
    Memoize the result of a property call.

    >>> class A(object):
    >>>     @memoize
    >>>     def func(self):
    >>>         return 'foo'
    """

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self
        d, n = vars(obj), self.__name__
        if n not in d:
            d[n] = self.func(obj)
        return d[n]


def once(func):
    """Runs a thing once and once only."""
    lock = threading.Lock()

    def new_func(*args, **kwargs):
        if new_func.called:
            return
        with lock:
            if new_func.called:
                return
            rv = func(*args, **kwargs)
            new_func.called = True
            return rv

    new_func = update_wrapper(new_func, func)
    new_func.called = False
    return new_func
