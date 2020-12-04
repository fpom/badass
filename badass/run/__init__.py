import json

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
    def __init__ (self, text, title="test", status=PASS, details=None) :
        self.text = text
        self.title = title
        self.status = status
        self.details = details
        self.checks = []
    def __json__ (self) :
        return {"status" : str(self.status).lower(),
                "title" : self.title,
                "text" : self.text,
                "checks" : self.checks,
                "details" : self.details}
    def add (self, status, text, title="test", details=None) :
        self.checks.append(_Test(text, title, status, details))
    def check (self, value, text, title="test", details=None) :
        self.add(PASS if bool(value) else FAIL, text, title, details)
    def any (self, text="any test must pass", title="test", details=None) :
        return _AnyTest(self, text, title, details)
    def all (self, text="all tests must pass", title="test", details=None) :
        return _AllTest(self, text, title, details)
    def not_any (self, text="all tests must fail", title="test", details=None) :
        return _NotAnyTest(self, text, title, details)
    def not_all (self, text="any test must fail", title="test", details=None) :
        return _NotAllTest(self, text, title)

class _NestedTest (_Test) :
    def __init__ (self, test, text, title="test", details=None) :
        super().__init__(text, title, details=details)
        self.test = test
    def __enter__ (self) :
        self._test_add, self.test.add = self.test.add, self.add
        return self
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self.test.add = self._test_add
        self.status = self._reduce(t.status for t in self.checks)
        self.test.checks.append(self)

class _AllTest (_NestedTest) :
    def _reduce (self, stats) :
        return _Status.all(PASS, *stats)

class _AnyTest (_NestedTest) :
    def _reduce (self, stats) :
        return _Status.any(FAIL, *stats)

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
    def __init__ (self, text, title="test") :
        super().__init__(text, title)
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
        self.status = _AllTest._reduce(self, (t.status for t in self.checks))
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
        rmtree(self.test_dir)
        self.TESTS.append(test_zip)
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
    def has (self, signature) :
        self.check(self.lang.decl(signature),
                   f"code declares `{mdesc(signature)}`")
    def query (self, pattern) :
        return [found for expr in expand(pattern, self.lang)
                for found in query(expr, self.lang.source.ast)]
    def run (self, stdin=None, eol=True) :
        return Run(self, stdin, eol)

##
##
##

class Run (_AllTest) :
    def __init__ (self, test, stdin=None, eol=True) :
        if stdin :
            text = f"build and execute program with input `{mdesc(stdin)}`"
        else :
            text = f"build and execute program"
        super().__init__(test, title="run", text=text)
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
        self_checks, self.checks = self.checks, []
        for title, text, name in (("compile", "compile every source file", "build"),
                                  ("memory", "safety checks", "memchk")) :
            checks = list(getattr(self.test.lang, f"report_{name}")())
            if checks :
                with _AllTest(self, title=title, text=text) as test :
                    for status, title, text, details in checks :
                        test.add(status, text, title, details)
        self.checks.extend(self_checks)
        super().__exit__(exc_type, exc_val, exc_tb)
    def get (self, text) :
        text = str(text)
        try :
            self.log.write(f"expect: {text!r}\n")
            self.process.expect(text)
            self.log.write(f"got: {self.process.match.group()!r}\n")
            self.add(PASS, f"program prints `{mdesc(text)}`")
        except EOF :
            self.log.write("error: end of file\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got end-of-file")
            self.terminate()
        except TIMEOUT :
            self.log.write("error: timeout\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got timeout")
            self.terminate()
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            self.add(FAIL, f"program prints `{mdesc(text)}`: got internal error")
            self.terminate()
    def put (self, text, eol=True) :
        text = str(text)
        try :
            self.log.write(f"send: `{mdesc(text)}`\n")
            if eol :
                self.process.sendline(text)
            else :
                self.process.send(text)
            self.test.add(PASS, f"program reads `{mdesc(text)}`")
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            self.add(FAIL, f"program reads `{mdesc(text)}`: got internal error")
            self.terminate()
    def terminate (self) :
        if self._exit_code is not None or self._signal is not None :
            return
        try :
            self.log.write("terminate: reading until EOF\n")
            self.process.expect(pexpect.EOF)
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
        try :
            self.log.write("terminate: closing\n")
            self.process.close(force=False)
            sleep(CONFIG.timeout)
            if self.process.isalive() :
                self.log.write(f"terminate: force-closing\n")
                self.process.close(force=True)
        except Exception as err :
            self.log.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
        self._exit_code = self.process.exitstatus
        self._signal = self.process.signalstatus
    @cached_property
    def stdout (self) :
        self.terminate()
        return self.stdout_log.read_text(**encoding)
    @cached_property
    def stderr (self) :
        self.terminate()
        return self.stderr_log.read_text(**encoding)
    @cached_property
    def exit_code (self) :
        self.terminate()
        return self._exit_code
    @cached_property
    def signal (self) :
        self.terminate()
        return self._signal
    @cached_property
    def process (self) :
        self.stdout_log = self.test.add_path(name="stdout.log", log="run")
        self.stderr_log = self.test.add_path(name="stderr.log", log="run")
        self.make_sh = self.test.add_path(prefix="make-", suffix=".sh")
        self.test.more_files["src/make.sh"] = self.make_sh
        self.test.lang.make_script(self.make_sh)
        child = pexpect.spawn("firejail",
                              ["--quiet", "--allow-debuggers",
                               "/bin/bash", self.make_sh.name],
                              cwd=str(self.test.test_dir),
                              timeout=CONFIG.timeout,
                              echo=False,
                              encoding=encoding.encoding,
                              codec_errors=encoding.errors)
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
