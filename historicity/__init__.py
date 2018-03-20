import os
import imp
import sys
import ast
import uuid
import errno
import types
import marshal
import inspect
import funcsigs
import functools
import contextlib
from threading import Thread
from time import time as now
if sys.version_info > (3, 0):
    from queue import Queue
else:
    from Queue import Queue

_ignores = set()
_include = set()
_archives = []


def include(*names):
    _include.update(names)


def ignore(*names):
    _ignores.update(names)


def archive(function):
    if function not in _archives:
        _archives.append(function)
    return function


class _Finder(object):

    def find_module(self, fullname, path=None):
        # filter out unwanted modules
        for i in _ignores:
            if fullname.startswith(i):
                return
        for i in _include:
            if fullname.startswith(i):
                break
        else:
            return
        # we want to modify this module
        if path in (None, ''):
            path = [os.getcwd()] # top level import
        if '.' in fullname:
            parents, name = fullname.rsplit('.', 1)
        else:
            name = fullname
        for entry in path:
            if os.path.isdir(os.path.join(entry, name)):
                # this module has child modules
                filename = os.path.join(entry, name, '__init__.py')
                submodule_locations = [os.path.join(entry, name)]
            else:
                filename = os.path.join(entry, name + '.py')
                submodule_locations = None
            if not os.path.exists(filename):
                continue
            return _Loader(filename)


class _Loader(object):

    def __init__(self, filename):
        self.filename = filename

    def load_module(self, name):
        if name in sys.modules:
            return sys.modules[name]
        else:
            new = types.ModuleType(name)
            self._exec_module(new)
            return new

    def _exec_module(self, module):
        saver = '_saver' + str(int(uuid.uuid4()))
        code = self._compile_module(module, saver)
        with open(self._cache(module), 'wb+') as f:
            f.write(imp.get_magic())
            marshal.dump(code, f)
        setattr(module, saver, _Saver())
        exec(code, vars(module))
        delattr(module, saver)

    def _compile_module(self, module, saver):
        aug = _Augmenter(module, saver)
        with open(self.filename) as f:
            tree = aug.parse(f.read())
        return compile(tree, self.filename, 'exec')

    def _cache(self, module):
        if hasattr(imp, 'get_tag'):
            tag = imp.get_tag() + '-historicity'
        else:
            if hasattr(sys, 'pypy_version_info'):
                impl = 'pypy'
            elif sys.platform == 'java':
                impl = 'jython'
            else:
                impl = 'cpython'
            ver = sys.version_info
            tag = '%s-%s%s-historicity' % (impl, ver[0], ver[1])
        ext = '.py' + (__debug__ and 'c' or 'o')
        tail = '.' + tag + ext

        cache_dir = os.path.join(os.path.dirname(self.filename), '__pycache__')
        try:
            os.mkdir(cache_dir)
        except OSError:
            e = sys.exc_info()[1].errno
            if e == errno.EEXIST:
                # Either the __pycache__ directory already exists (the
                # common case) or it's blocked by a non-dir node. In the
                # latter case, we'll ignore it in _write_pyc.
                pass
            elif e in [errno.ENOENT, errno.ENOTDIR]:
                # One of the path components was not a directory, likely
                # because we're in a zip file.
                write = False
            else:
                raise
        return os.path.join(cache_dir, module.__name__ + tail)


class _Augmenter(ast.NodeTransformer):

    def __init__(self, module, saver):
        self._module = module.__name__
        self._saver = saver

    @contextlib.contextmanager
    def stack(self, node):
        is_definition = type(node) in (ast.FunctionDef, ast.ClassDef)
        if is_definition:
            self._stack.append(node)
        yield
        if is_definition:
            self._stack.pop()

    def parse(self, text):
        self._stack = []
        tree = self.visit(ast.parse(text))
        return ast.fix_missing_locations(tree)

    def visit(self, node):
        with self.stack(node):
            node = super(_Augmenter, self).visit(node)
        return node

    def visit_FunctionDef(self, node):
        if not node.name.startswith('_'):
            definition = self._module
            if self._stack:
                definition += '::' + '.'.join(n.name for n in self._stack)
            node.decorator_list.append(ast.Attribute(
                    ast.Name(self._saver, ast.Load()),
                    definition, ast.Load()))
        return node


class _Saver(object):

    def __getattr__(self, definition):
        # I don't know why I can't use a standard
        # ast.Call inside the node decorator, so
        # this will have to suffice.
        for i in _ignores:
            if definition.startswith(i):
                return lambda function : function
        def setup(function):
            sig = funcsigs.signature(function)
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                bound = sig.bind_partial(*args, **kwargs)
                _send(definition, 'started', dict(bound.arguments))
                try:
                    result = function(*args, **kwargs)
                except Exception as e:
                    _send(definition, 'failure', e)
                    raise
                else:
                    _send(definition, 'success', result)
                return result
            return wrapper
        return setup


class _Here(object):

    def find_module(self, fullname, path=None):
        if fullname == __name__ + '.include':
            frame = inspect.currentframe().f_back
            include(frame.f_globals['__name__'])
            return self

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]
        return include

QUEUE = Queue()


def _send(function, state, message):
    try:
        message = json.dumps(message)
    except:
        message = str(message)
    QUEUE.put((function, state, message))


def _save():
    while True:
        function, state, message = QUEUE.get()
        for archive in _archives:
            archive(function, state, message)


_THREAD = Thread(target=_save)
_THREAD.deamon = True
_THREAD.start()


sys.meta_path[:0] = [_Here(), _Finder()]
