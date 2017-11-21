from __future__ import absolute_import

import os
import time
import logging
from types import FunctionType

from raven.utils.compat import iteritems, get_code, text_type, string_types
from raven.utils import once


special_logging_handlers = []
special_logger_handlers = {}


logger = logging.getLogger('raven')


def event_payload_considered_equal(a, b):
    return (
        a['type'] == b['type'] and
        a['level'] == b['level'] and
        a['message'] == b['message'] and
        a['category'] == b['category'] and
        a['data'] == b['data']
    )


class BreadcrumbBuffer(object):

    def __init__(self, limit=100):
        self.buffer = []
        self.limit = limit

    def record(self, timestamp=None, level=None, message=None,
               category=None, data=None, type=None, processor=None):
        if not (message or data or processor):
            raise ValueError('You must pass either `message`, `data`, '
                             'or `processor`')
        if timestamp is None:
            timestamp = time.time()
        self.buffer.append(({
            'type': type or 'default',
            'timestamp': timestamp,
            'level': level,
            'message': message,
            'category': category,
            'data': data,
        }, processor))
        del self.buffer[:-self.limit]

    def clear(self):
        del self.buffer[:]

    def get_buffer(self):
        rv = []
        for idx, (payload, processor) in enumerate(self.buffer):
            if processor is not None:
                try:
                    processor(payload)
                except Exception:
                    logger.exception('Failed to process breadcrumbs. Ignored')
                    payload = None
                self.buffer[idx] = (payload, None)
            if payload is not None and \
               (not rv or not event_payload_considered_equal(rv[-1], payload)):
                rv.append(payload)
        return rv


class BlackholeBreadcrumbBuffer(BreadcrumbBuffer):
    def record(self, *args, **kwargs):
        pass


def make_buffer(enabled=True):
    if enabled:
        return BreadcrumbBuffer()
    return BlackholeBreadcrumbBuffer()


def record_breadcrumb(type, *args, **kwargs):
    # Legacy alias
    kwargs['type'] = type
    return record(*args, **kwargs)


def record(message=None, timestamp=None, level=None, category=None,
           data=None, type=None, processor=None):
    """Records a breadcrumb for all active clients.  This is what integration
    code should use rather than invoking the `captureBreadcrumb` method
    on a specific client.
    """
    if timestamp is None:
        timestamp = time.time()
    for ctx in raven.context.get_active_contexts():
        ctx.breadcrumbs.record(timestamp, level, message, category,
                               data, type, processor)


def _record_log_breadcrumb(logger, level, msg, *args, **kwargs):
    for handler in special_logging_handlers:
        rv = handler(logger, level, msg, args, kwargs)
        if rv:
            return

    handler = special_logger_handlers.get(logger.name)
    if handler is not None:
        rv = handler(logger, level, msg, args, kwargs)
        if rv:
            return

    def processor(data):
        formatted_msg = msg

        # If people log bad things, this can happen.  Then just don't do
        # anything.
        try:
            formatted_msg = text_type(msg)
            if args:
                formatted_msg = msg % args
        except Exception:
            pass

        # We do not want to include exc_info as argument because it often
        # lies (set to a constant value like 1 or True) or even if it's a
        # tuple it will not be particularly useful for us as we cannot
        # process it anyways.
        kwargs.pop('exc_info', None)
        data.update({
            'message': formatted_msg,
            'category': logger.name,
            'level': logging.getLevelName(level).lower(),
            'data': kwargs,
        })
    record(processor=processor)


def _wrap_logging_method(meth, level=None):
    if not isinstance(meth, FunctionType):
        func = meth.im_func
    else:
        func = meth

    # We were patched for raven before
    if getattr(func, '__patched_for_raven__', False):
        return

    if level is None:
        args = ('level', 'msg')
        fwd = 'level, msg'
    else:
        args = ('msg',)
        fwd = '%d, msg' % level

    code = get_code(func)

    logging_srcfile = logging._srcfile
    if logging_srcfile is None:
        logging_srcfile = os.path.normpath(
            logging.currentframe.__code__.co_filename
        )

    # This requires a bit of explanation why we're doing this.  Due to how
    # logging itself works we need to pretend that the method actually was
    # created within the logging module.  There are a few ways to detect
    # this and we fake all of them: we use the same function globals (the
    # one from the logging module), we create it entirely there which
    # means that also the filename is set correctly.  This fools the
    # detection code in logging and it makes logging itself skip past our
    # code when determining the code location.
    #
    # Because we point the globals to the logging module we now need to
    # refer to our own functions (original and the crumb recording
    # function) through a closure instead of the global scope.
    #
    # We also add a lot of newlines in front of the code so that the
    # code location lines up again in case someone runs inspect.getsource
    # on the function.
    ns = {}
    eval(compile('''%(offset)sif 1:
    def factory(original, record_crumb):
        def %(name)s(self, %(args)s, *args, **kwargs):
            record_crumb(self, %(fwd)s, *args, **kwargs)
            return original(self, %(args)s, *args, **kwargs)
        return %(name)s
    \n''' % {
        'offset': '\n' * (code.co_firstlineno - 3),
        'name': func.__name__,
        'args': ', '.join(args),
        'fwd': fwd,
        'level': level,
    }, logging_srcfile, 'exec'), logging.__dict__, ns)

    new_func = ns['factory'](meth, _record_log_breadcrumb)
    new_func.__doc__ = func.__doc__

    assert code.co_firstlineno == get_code(func).co_firstlineno

    # In theory this should already be set correctly, but in some cases
    # it is not.  So override it.
    new_func.__module__ == func.__module__
    new_func.__name__ == func.__name__
    new_func.__patched_for_raven__ = True

    return new_func


def _patch_logger():
    cls = logging.Logger

    methods = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'warn': logging.WARN,
        'error': logging.ERROR,
        'exception': logging.ERROR,
        'critical': logging.CRITICAL,
        'fatal': logging.FATAL
    }

    for method_name, level in iteritems(methods):
        new_func = _wrap_logging_method(
            getattr(cls, method_name), level)
        setattr(logging.Logger, method_name, new_func)

    logging.Logger.log = _wrap_logging_method(
        logging.Logger.log)


@once
def install_logging_hook():
    """Installs the logging hook if it was not installed yet.  Otherwise
    does nothing.
    """
    _patch_logger()


def ignore_logger(name_or_logger, allow_level=None):
    """Ignores a logger for the regular breadcrumb code.  This is useful
    for framework integration code where some log messages should be
    specially handled.
    """
    def handler(logger, level, msg, args, kwargs):
        if allow_level is not None and \
           level >= allow_level:
            return False
        return True
    register_special_log_handler(name_or_logger, handler)


def register_special_log_handler(name_or_logger, callback):
    """Registers a callback for log handling.  The callback is invoked
    with give arguments: `logger`, `level`, `msg`, `args` and `kwargs`
    which are the values passed to the logging system.  If the callback
    returns `True` the default handling is disabled.
    """
    if isinstance(name_or_logger, string_types):
        name = name_or_logger
    else:
        name = name_or_logger.name
    special_logger_handlers[name] = callback


def register_logging_handler(callback):
    """Registers a callback for log handling.  The callback is invoked
    with give arguments: `logger`, `level`, `msg`, `args` and `kwargs`
    which are the values passed to the logging system.  If the callback
    returns `True` the default handling is disabled.
    """
    special_logging_handlers.append(callback)


hooked_libraries = {}


def libraryhook(name):
    def decorator(f):
        f = once(f)
        hooked_libraries[name] = f
        return f
    return decorator


@libraryhook('requests')
def _hook_requests():
    try:
        from requests.sessions import Session
    except ImportError:
        return

    real_send = Session.send

    def send(self, request, *args, **kwargs):
        def _record_request(response):
            record(type='http', category='requests', data={
                'url': request.url,
                'method': request.method,
                'status_code': response and response.status_code or None,
                'reason': response and response.reason or None,
            })
        try:
            resp = real_send(self, request, *args, **kwargs)
        except Exception:
            _record_request(None)
            raise
        else:
            _record_request(resp)
        return resp

    Session.send = send

    ignore_logger('requests.packages.urllib3.connectionpool',
                  allow_level=logging.WARNING)


@libraryhook('httplib')
def _install_httplib():
    try:
        from httplib import HTTPConnection
    except ImportError:
        from http.client import HTTPConnection

    real_putrequest = HTTPConnection.putrequest
    real_getresponse = HTTPConnection.getresponse

    def putrequest(self, method, url, *args, **kwargs):
        self._raven_status_dict = status = {}
        host = self.host
        port = self.port
        default_port = self.default_port

        def processor(data):
            real_url = url
            if not real_url.startswith(('http://', 'https://')):
                real_url = '%s://%s%s%s' % (
                    default_port == 443 and 'https' or 'http',
                    host,
                    port != default_port and ':%s' % port or '',
                    url,
                )
            data['data'] = {
                'url': real_url,
                'method': method,
            }
            data['data'].update(status)
            return data
        record(type='http', category='requests', processor=processor)
        return real_putrequest(self, method, url, *args, **kwargs)

    def getresponse(self, *args, **kwargs):
        rv = real_getresponse(self, *args, **kwargs)
        status = getattr(self, '_raven_status_dict', None)
        if status is not None and 'status_code' not in status:
            status['status_code'] = rv.status
            status['reason'] = rv.reason
        return rv

    HTTPConnection.putrequest = putrequest
    HTTPConnection.getresponse = getresponse


def hook_libraries(libraries):
    if libraries is None:
        libraries = hooked_libraries.keys()
    for lib in libraries:
        func = hooked_libraries.get(lib)
        if func is None:
            raise RuntimeError('Unknown library %r for hooking' % lib)
        func()


import raven.context
