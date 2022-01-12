import json, os, ast, sys, uuid

from pathlib import Path
from shutil import copytree, rmtree, copy2 as copy
from time import sleep
from zipfile import ZipFile, ZIP_LZMA
from collections import defaultdict
from traceback import print_tb as _print_tb
from tempfile import mkdtemp, mkstemp
from subprocess import run as subprocess_run, PIPE, STDOUT

from ..lang import load as load_lang
from .. import tree, new_path, encoding, cached_property, JSONEncoder, mdesc
from .queries import query, expand
from .report import Report

import pexpect
from pexpect.exceptions import EOF, TIMEOUT

try :
    from colored_traceback import Colorizer
    coltb = Colorizer(style="default")
    def print_tb (exc_type, exc_val, exc_tb) :
        coltb.colorize_traceback(exc_type, exc_val, exc_tb)
        coltb.stream.write("\n")
except ImportError :
    def print_tb (exc_type, exc_val, exc_tb) :
        print("Traceback (most recent call last):", file=sys.stderr)
        _print_tb(exc_tb, file=sys.stderr)
        print(f"{exc_type.__name__}: {exc_val}", file=sys.stderr)

##
##
##

CONFIG = tree()
ARGS = tree()

##
##
##

class Repository (object) :
    def __init__ (self, basedir) :
        self.base = Path(basedir)
        self.content = {}
    def __iter__ (self) :
        yield from self.content.items()
    def walk (self, root=None) :
        if root is None :
            root = self.base
        else :
            root = Path(root)
        if root.is_file() :
            yield root
        elif root.is_dir() :
            for path in root.iterdir() :
                if path.is_file() :
                    yield path
                elif path.is_dir() :
                    yield from self.walk(path)
    def update (self, *roots, normalise=True) :
        if roots :
            tops = [Path(p) for r in roots for p in self.base.glob(r)]
        else :
            tops = [self.base]
        for root in tops :
            for path in self.walk(root) :
                if normalise :
                    newpath = path.with_suffix(path.suffix.lower())
                    path.rename(newpath)
                    path = newpath
                self.add(path)
    def add (self, path) :
        relpath = self.content[path] = Path(path).relative_to(self.base)
        return relpath
    def new (self, path) :
        path = Path(path)
        base = self.base / path.parent
        base.mkdir(exist_ok=True, parents=True)
        path = base / path.name
        if path.exists() :
            fd, path = mkstemp(prefix=path.stem + "-", suffix=path.suffix, dir=base)
            os.close(fd)
            path = self.base / Path(path).relative_to(self.base.resolve())
        else :
            path.touch()
        self.add(path)
        return path
    def copy (self, src, dst) :
        src, dst = Path(src), Path(dst)
        dst.parent.mkdir(exist_ok=True, parents=True)
        copy(src, dst)
        self.add(dst)
    def copytree (self, src, dst) :
        src = self.base / src
        dst = self.base / dst
        for path in self.walk(src) :
            self.copy(path, dst / path.relative_to(src))
    def zip (self, path) :
        with Path(path).open("wb") as out :
            with ZipFile(out, "w", compression=ZIP_LZMA, compresslevel=9) as zf :
                for path, alias in self :
                    zf.write(path, alias)

##
##
##

class _Status (int) :
    _str = {-1 : "FAIL", 0 : "WARN", 1 : "PASS"}
    _num = {-1 : None, 0 : None, 1 : None}
    all = min
    any = max
    def __new__ (cls, num) :
        if cls._num[num] is None :
            cls._num[num] = int.__new__(cls, num)
        return cls._num[num]
    def __str__ (self) :
        return self._str[self]
    def __repr__ (self) :
        return str(self)
    def __json__ (self) :
        return str(self)
    def __and__ (self, other) :
        return self.all(self, other)
    def __or__ (self, other) :
        return self.any(self, other)
    def __invert__ (self) :
        return self._num[-self]

PASS = _Status(1)
WARN = _Status(0)
FAIL = _Status(-1)

class _Test (object) :
    def __init__ (self, text, status=PASS, details=None, auto=False) :
        self.text = text
        self.status = status
        self.details = details
        self.auto = auto
        self.checks = []
    def __json__ (self) :
        return {"status" : str(self.status).lower(),
                "text" : self.text,
                "checks" : self.checks,
                "details" : self.details,
                "auto" : self.auto}
    def add (self, status, text, details=None, auto=False) :
        self.checks.append(_Test(text, status, details, auto))
    def check (self, value, text, details=None, auto=False) :
        self.add(PASS if bool(value) else FAIL, text, details, auto)
        return bool(value)
    def any (self, text="at least one test must pass", details=None, auto=False) :
        return _AnyTest(self, text, details, auto)
    def all (self, text="all tests must pass", details=None, auto=False) :
        return _AllTest(self, text, details, auto)
    def not_any (self, text="all tests must fail", details=None, auto=False) :
        return _NotAnyTest(self, text, details, auto)
    def not_all (self, text="at least one test must fail", details=None, auto=False) :
        return _NotAllTest(self, text, details, auto)

class _NestedTest (_Test) :
    def __init__ (self, test, text, details=None, auto=False) :
        super().__init__(text, details=details, auto=auto)
        self.test = test
    def __enter__ (self) :
        self._test_add, self.test.add = self.test.add, self.add
        return self
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self.test.add = self._test_add
        if exc_type is None :
            self.status = self._reduce(t.status for t in self.checks)
        else :
            if CONFIG.debug :
                print_tb(exc_type, exc_val, exc_tb)
            self.status = FAIL
        self.test.checks.append(self)
        return True

class _AllTest (_NestedTest) :
    def _reduce (self, stats) :
        return _Status.all(PASS, PASS, *stats)

class _AnyTest (_NestedTest) :
    def _reduce (self, stats) :
        return _Status.any(FAIL, FAIL, *stats)

class _NotAllTest (_AllTest) :
    def _reduce (self, stats) :
        return ~ super()._reduce(stats)

class _NotAnyTest (_AnyTest) :
    def _reduce (self, stats) :
        return ~ super()._reduce(stats)

##
##
##

class Test (_Test) :
    NUM = 0
    TESTS = []
    def __init__ (self, text) :
        super().__init__(text)
        self.project_dir = Path(CONFIG.project)
        self.lang_mod = load_lang(CONFIG.lang)
        self.num = self.__class__.NUM = self.__class__.NUM + 1
        self.test_dir = self.project_dir / f"test-{self.num:03}"
        self.repo = Repository(self.test_dir)
    def __enter__ (self) :
        copytree(self.project_dir / "src", self.test_dir / "src")
        self.repo.update()
        return self
    @cached_property
    def lang (self) :
        return self.lang_mod.Language(self)
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        if exc_type is None :
            self.status = _AllTest._reduce(self, (t.status for t in self.checks))
        else :
            if CONFIG.debug :
                print_tb(exc_type, exc_val, exc_tb)
            self.status = FAIL
        test_json = self.repo.new("test.json")
        with test_json.open("w", **encoding) as out :
            json.dump(self, out, ensure_ascii=False, cls=JSONEncoder)
        self.repo.update("log")
        test_zip = self.test_dir.with_suffix(".zip")
        self.repo.zip(test_zip)
        if not CONFIG.keep :
            rmtree(self.test_dir, ignore_errors=True)
        self.TESTS.append(test_zip)
        return True
    def add_source (self, source) :
        path = self.repo.new(f"src/test{self.lang.SUFFIX}")
        self.lang.add_source(source, path)
    def del_source (self, name) :
        self.lang.del_source(name)
    def has (self, signature, declarations=None) :
        return self.check(self.lang.decl(signature, declarations),
                          f"code declares `{mdesc(signature)}`")
    def query (self, pattern, parser="clang", tree=None) :
        if tree is None :
            if parser is not None :
                tree = {k : v[parser] for k, v in self.lang.source.ast.items()}
            else :
                tree = self.lang.source.ast
        return [found for expr in expand(pattern, self.lang)
                for found in query(expr, tree)]
    def run (self, stdin=None, eol=True, timeout=None, **options) :
        return Run(self, stdin, eol, timeout, **options)

##
##
##

_diag2status = {"info" : PASS,
                "warning" : WARN,
                "error" : FAIL}

class Run (_AllTest) :
    def __init__ (self, test, stdin=None, eol=True, timeout=None, **options) :
        if stdin :
            text = f"build and execute program with input `{mdesc(stdin)}`"
        else :
            text = f"build and execute program"
        super().__init__(test, text=text)
        self.timeout = timeout or CONFIG.timeout
        self.stdin = stdin
        self.eol = eol
        self._exit_code = None
        self._signal = None
        self._stop = None
        self.options = defaultdict(dict)
        for k, v in options.items() :
            try :
                c, n = k.split("_", 1)
            except :
                raise TypeError(f"unknown option '{k}'")
            self.options[c][n] = v
    def __enter__ (self) :
        super().__enter__()
        self.log_path = self.test.repo.new("log/run/run.log")
        return self
    @property
    def log (self) :
        return self.log_path.open("a", **encoding)
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self.terminate("end of test")
        self_checks, self.checks = self.checks, []
        for title, name, checks in self.test.lang.checks() :
            with _AllTest(self, text=title) as test :
                for status, text, details, info in checks :
                    if info :
                        with _AllTest(test, text=text, details=details) as sub :
                            for diag, message, pos, before, after in info :
                                sub.add(_diag2status[diag],
                                        text=(f"`[{pos.path}:{pos.line}:{pos.col}]`"
                                              f" {message}"),
                                        details=(f"`{before.replace(' ', '§')}`"
                                                 f"**`{after.replace(' ', '§')}`**"),
                                        auto=True)
                    elif name == "memchk" :
                        test.add(WARN, text, details, auto=True)
                    else :
                        test.add(PASS if status else FAIL, text, details, auto=True)
        self.checks.extend(self_checks)
        return super().__exit__(exc_type, exc_val, exc_tb)
    def get (self, text) :
        if self.terminated :
            return
        text = str(text)
        try :
            self.log.write(f"expect: {text!r}\n")
            self.process.expect(text)
            self.log.write(f"got: {self.process.match.group()!r}\n")
            self.add(PASS, f"program prints `{mdesc(text)}`")
        except EOF :
            self.log.write("error: end of file\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got end-of-file")
            self.terminate("end of stdout")
        except TIMEOUT :
            self.log.write("error: timeout\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got timeout")
            self.terminate("timeout")
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got internal error")
            self.terminate("error")
    def put (self, text, eol=True) :
        if self.terminated :
            return
        text = str(text)
        try :
            self.log.write(f"send: `{mdesc(text)}`\n")
            if eol :
                self.process.sendline(text)
            else :
                self.process.send(text)
            self.add(PASS, f"program reads `{mdesc(text)}`")
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            self.add(FAIL, f"program reads `{mdesc(text)}`: got internal error")
            self.terminate("error")
    @property
    def terminated (self) :
        return self._exit_code is not None or self._signal is not None
    def terminate (self, reason=None) :
        if self.terminated :
            return
        # ensure that process has been started
        self.process
        self._exit_reason = reason
        if self._stop is not None :
            self.log.write("terminate: requesting program to stop\n")
            sleep(self.timeout)
            log = self.test.repo.new("log/run/stop.log")
            done = subprocess_run(["firejail", "--quiet",
                                   f"--join={self._jail}",
                                   "/bin/bash", str(self._stop.name)],
                                  stdout=PIPE, stderr=STDOUT, **encoding,
                                  cwd=str(self.test.test_dir),
                                  env={var : os.environ[var]
                                       for var in ("PATH", "TERM", "LC_ALL")
                                       if var in os.environ})
            with log.open("w", **encoding) as out :
                out.write(done.stdout)
            sleep(1)
        try :
            self.log.write("terminate: reading until EOF\n")
            self.process.expect(pexpect.EOF)
        except TIMEOUT :
            self.log.write("error: timeout\n")
            self._exit_reason = "timeout"
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
        try :
            self.log.write("terminate: closing\n")
            self.process.close(force=False)
            sleep(self.timeout)
            if self.process.isalive() :
                self.log.write(f"terminate: force-closing\n")
                self.process.close(force=True)
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
        try :
            self.process.logfile_read.close()
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
        try :
            self.log.close()
        except :
            pass
        if self.test.lang.exit_code :
            self._exit_code = self.test.lang.exit_code
        else :
            self._exit_code = self.process.exitstatus
        self._signal = self.process.signalstatus
    @cached_property
    def exit_reason (self) :
        self.terminate("exit reason requested")
        return self._exit_reason
    @cached_property
    def stdout (self) :
        self.terminate("stdout requested")
        return self.stdout_log.read_text(**encoding)
    @cached_property
    def exit_code (self) :
        self.terminate("exit code requested")
        return self._exit_code
    @cached_property
    def signal (self) :
        self.terminate("signal requested")
        return self._signal
    @cached_property
    def process (self) :
        self.stdout_log = self.test.repo.new("log/run/stdout.log")
        script, self._stop = self.test.lang.make_script(**self.options["script"])
        self.test.repo.add(script)
        if self._stop is not None :
            self.test.repo.add(self._stop)
        self._jail = uuid.uuid4().hex
        child = pexpect.spawn("firejail",
                              ["--quiet", "--allow-debuggers", "--private=.",
                               f"--name={self._jail}",
                               "/bin/bash", str(script.name)],
                              cwd=str(self.test.test_dir),
                              timeout=self.timeout,
                              echo=False,
                              encoding=encoding.encoding,
                              codec_errors=encoding.errors,
                              env={var : os.environ[var]
                                   for var in ("PATH", "TERM", "LC_ALL")
                                   if var in os.environ})
        child.logfile_read = self.stdout_log.open("w", **encoding)
        if self.stdin is not None :
            if self.eol :
                child.sendline(str(self.stdin))
            else :
                child.send(str(self.stdin))
        return child
    @cached_property
    def strace (self) :
        self.terminate("strace requested")
        return self.test.lang.strace()

##
##
##

def report () :
    rep = Report(Path(CONFIG.project), Test.TESTS)
    rep.save()
