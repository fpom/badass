import json, os

from pathlib import Path
from shutil import copytree, rmtree
from time import sleep
from zipfile import ZipFile, ZIP_LZMA

from ..lang import load as load_lang
from .. import tree, new_path, encoding, cached_property, JSONEncoder, mdesc
from .queries import query, expand
from .report import Report

import pexpect
from pexpect.exceptions import EOF, TIMEOUT

##
##
##

CONFIG = tree()
ARGS = tree()

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
        self.lang_class = load_lang(CONFIG.lang)
        self.num = self.__class__.NUM = self.__class__.NUM + 1
    def __enter__ (self) :
        self.test_dir = self.project_dir / f"test-{self.num:03}"
        copytree(self.project_dir / "src", self.test_dir)
        for path in self._walk() :
            norm = path.with_suffix(path.suffix.lower())
            if path != norm :
                path.rename(norm)
        self.source_files = list(self._walk())
        self.more_files = {}
        self.log_dir = self.add_path(type="dir", prefix="log-")
        self.report_dir = self.add_path(type="dir", prefix="report-")
        return self
    @cached_property
    def lang (self) :
        return self.lang_class.Language(self)
    def _walk (self, root=None) :
        if root is None :
            root = self.test_dir
        for path in root.iterdir() :
            if path.is_file() :
                yield path
            elif path.is_dir() :
                yield from self._walk(path)
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        if exc_type is None :
            self.status = _AllTest._reduce(self, (t.status for t in self.checks))
        else :
            self.status = FAIL
        with (self.report_dir / "test.json").open("w", **encoding) as out :
            json.dump(self, out, ensure_ascii=False, cls=JSONEncoder)
        test_zip = self.test_dir.with_suffix(".zip")
        with test_zip.open("wb") as out :
            with ZipFile(out, "w", compression=ZIP_LZMA, compresslevel=9) as zf :
                for path in self.report_dir.glob("*.json") :
                    zf.write(path, path.name)
                for path in self.source_files :
                    zf.write(path, Path("src") / path.relative_to(self.test_dir))
                for tgt, src in self.more_files.items() :
                    zf.write(src, tgt)
                for path in self._walk(self.log_dir) :
                    zf.write(path, Path("log") / path.relative_to(self.log_dir))
        if not CONFIG.keep :
            rmtree(self.test_dir, ignore_errors=True)
        self.TESTS.append(test_zip)
        return True
    def add_path (self, log=None, name=None, **args) :
        if log is True :
            args["dir"] = self.log_dir
        elif log :
            args["dir"] = self.log_dir / log
        else :
            args["dir"] = self.test_dir
        if name :
            path = args["dir"] / name
            path.parent.mkdir(exist_ok=True, parents=True)
            path.open("w").close()
            return path
        else :
            return new_path(**args)
    def add_source (self, source) :
        path = self.add_path(prefix="test-", suffix=self.lang.SUFFIX)
        self.lang.add_source(source, path)
        self.source_files.append(path)
    def del_source (self, name) :
        self.lang.del_source(name)
    def has (self, signature, declarations=None) :
        self.check(self.lang.decl(signature, declarations),
                   f"code declares `{mdesc(signature)}`")
    def query (self, pattern) :
        return [found for expr in expand(pattern, self.lang)
                for found in query(expr, self.lang.source.ast)]
    def run (self, stdin=None, eol=True, timeout=None) :
        return Run(self, stdin, eol, timeout)

##
##
##

_diag2status = {"info" : PASS,
                "warning" : WARN,
                "error" : FAIL}

class Run (_AllTest) :
    def __init__ (self, test, stdin=None, eol=True, timeout=None) :
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
    def __enter__ (self) :
        super().__enter__()
        self.log_path = self.test.add_path(name="run.log", log="run")
        self.log = self.log_path.open("w", **encoding)
        return self
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self.terminate("end of test")
        self_checks, self.checks = self.checks, []
        for title, name in (("compile and link", "build"),
                            ("memory safety checks", "memchk")) :
            checks = list(getattr(self.test.lang, f"report_{name}")())
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
        self._exit_reason = reason
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
        self.stdout_log = self.test.add_path(name="stdout.log", log="run")
        self.make_sh = self.test.add_path(prefix="make-", suffix=".sh")
        self.test.more_files["src/make.sh"] = self.make_sh
        self.test.lang.make_script(self.make_sh)
        child = pexpect.spawn("firejail",
                              ["--quiet", "--allow-debuggers", "--private=.",
                               "/bin/bash", self.make_sh.name],
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

##
##
##

def report () :
    rep = Report(Path(CONFIG.project), Test.TESTS)
    rep.save()
