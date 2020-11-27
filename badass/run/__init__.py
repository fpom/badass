import pathlib, itertools, shutil, shlex, tempfile, os, subprocess, zipfile, json, inspect
import sys, pexpect, time
from ast import literal_eval
from datetime import timedelta
from ..lang import load as load_lang
from .. import tree

class ScriptError (Exception) :
    pass

class Line (str) :
    def __new__ (cls, path, num, text, raw) :
        return super().__new__(cls, text)
    def __init__ (self, path, num, text, raw) :
        self.path = path
        self.num = num
        self.raw = raw
    @property
    def eof (self) :
        return self.raw is None
    @property
    def pos (self) :
        return f"{self.path}:{self.num}"

class ScriptSource (object) :
    def __init__ (self, script) :
        self.path = script.name
        self.lines = tuple(Line(self.path, n+1, l.rstrip(), l)
                           for n, l in enumerate(script))
        self.lno = -1
        self.EOF = Line(self.path, len(self.lines)+1, None, None)
    def back (self, n=1) :
        self.lno = max(-1, self.lno - n)
    @property
    def last (self) :
        try :
            return self.lines[self.lno]
        except :
            pass
    def __iter__ (self) :
        stop = len(self.lines) - 1
        while self.lno < stop :
            self.lno += 1
            yield self.lines[self.lno]
        while True :
            yield self.EOF

def literal (text) :
    try :
        return literal_eval(text)
    except :
        return text

class IOChecker (object) :
    def __init__ (self, arguments=sys.argv[1:], timeout=1) :
        self.timeout = timeout
        stdout = stdin = None
        argv = []
        for pos, arg in enumerate(arguments) :
            if arg.startswith("--stdout=") :
                stdout = arg.split("=", 1)[1]
            elif arg.startswith("--stdin=") :
                stdin = arg.split("=", 1)[1]
            else :
                argv.extend(arguments[pos:])
                break
        self.child = pexpect.spawn(argv[0], argv[1:],
                                   timeout=timeout,
                                   encoding="utf-8",
                                   codec_errors="ignore")
        if stdout :
            self.child.logfile_read = open(stdout, "w", encoding="utf-8")
        if stdin :
            self.child.logfile_send = open(stdin, "w", encoding="utf-8")
    def send (self, text) :
        try :
            sys.stderr.write(f"send: {text!r}\n")
            self.child.send(text)
            self.child.expect(text)
        except Exception as err :
            sys.stderr.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            sys.exit(1)
    def expect (self, text) :
        try :
            sys.stderr.write(f"expect: {text!r}\n")
            self.child.expect(text)
            sys.stderr.write(f"got: {self.child.match.group()!r}\n")
        except Exception as err :
            sys.stderr.write(f"error: {err.__class__.__name__}: {repr(str(err))}\n")
            sys.exit(1)
    def exit (self) :
        try :
            self.child.close(force=False)
            time.sleep(self.timeout)
            if self.child.isalive() :
                sys.stderr.write(f"close: FORCE\n")
                self.child.close(force=True)
            else :
                sys.stderr.write(f"close: OK\n")
        except Exception as err :
            sys.stderr.write(f"close: {err.__class__.__name__}: {repr(str(err))}\n")
        sys.stderr.write(f"exit: {self.child.exitstatus} {self.child.signalstatus}\n")

class ScriptRunner (object) :
    def __init__ (self, project_dir, script, lang) :
        self.project_dir = pathlib.Path(project_dir).absolute()
        self.src = self.project_dir / "src"
        if not self.src.is_dir() :
            self._raise("invalid project", "missing 'src' directory")
        for num in itertools.count() :
            self.test_dir = self.project_dir / pathlib.Path(f"test-{num:03}")
            if not self.test_dir.exists() :
                break
        shutil.copytree(self.src, self.test_dir)
        self.source_files = list(self._find_files(self.test_dir))
        self.lang = load_lang(lang).Language(self.test_dir)
        self.script = ScriptSource(script)
        self.report = []
    def _find_files (self, root) :
        for path in root.iterdir() :
            if path.is_file() :
                yield path
            elif path.is_dir() :
                yield from self._find_files(path)
    def _raise (self, error, txt=None) :
        if isinstance(txt, Line) :
            if txt.eof :
                raise ScriptError(f"[{txt.pos}] {error}")
            else :
                raise ScriptError(f"[{txt.pos}] {error}: {txt}")
        elif txt :
            raise ScriptError(f"{error}: {txt}")
        else :
            raise ScriptError(f"{error}")
    def _mktmp (self, **args) :
        args["dir"] = self.test_dir
        fd, path = tempfile.mkstemp(**args)
        os.close(fd)
        return pathlib.Path(path)
    def run (self) :
        for line in self.script :
            if line.eof :
                break
            elif not line :
                continue
            cmd, *arguments = shlex.split(line, comments="#")
            if cmd.endswith(":") or (arguments and arguments[0] == ":") :
                cmd = cmd.rstrip(":")
                largs = [literal(line.split(":", 1)[1].strip())]
                kargs = {}
            else :
                largs = []
                kargs = {}
                for arg in arguments :
                    try :
                        key, val = arg.split("=", 1)
                        kargs[key.strip()] = literal(val)
                    except :
                        kargs[arg] = True
            handler = getattr(self, f"do_{cmd}", None)
            if handler is None :
                self._raise("unknow command", line)
            handler(*largs, **kargs)
    def do_test (self, text) :
        self.entry = tree(title="functional test",
                          text=text,
                          details=None,
                          status="pass")
        self.execenv = {}
    def do_exec (self, code) :
        exec(code, self.execenv, self.execenv)
    def do_run (self, interactive=False, until=None, timeout=1) :
        if until :
            code = []
            for line in self.script :
                if line == until :
                    break
                elif line.eof :
                    self._raise("unexpected end of file", line)
                code.append(line.raw)
            src = self._mktmp(prefix="test-", suffix=self.lang.SUFFIX)
            self.lang.prepare("".join(code), src.open("w", encoding="utf-8"),
                              self.source_files)
            self.source_files.append(src.relative_to(self.test_dir))
        self.run_timeout = self.expect_py = io_py = None
        if interactive :
            self.expect_py = self._mktmp(prefix="io-", suffix=".py")
            io_py = f"/usr/bin/python3 {self.expect_py.name}"
            self._mk_iochk(timeout)
        elif timeout :
            self.run_timeout = f"--timeout={timedelta(seconds=timeout)}"
        self.test_sh = self._mktmp(prefix="test-", suffix=".sh")
        with self.test_sh.open("w", encoding="utf-8") as test_out :
            self.lang.build(test_out, self.source_files)
            self.expect_io = self.lang.run(test_out, stdio=io_py)
    def _mk_iochk (self, timeout) :
        with self.expect_py.open("w", encoding="utf-8") as out :
            out.write("import sys, pexpect, time\n\n")
            out.write(inspect.getsource(IOChecker))
            out.write(f"\nchk = IOChecker(timeout={timeout})\n\n")
            for line in self.script :
                if not line :
                    break
                elif line and line[0] in "<>" :
                    text = line[1:].lstrip().format(**self.execenv)
                    if line[0] == ">" :
                        if text.endswith("\\") :
                            text = text[:-1]
                        else :
                            text += "\r\n"
                        out.write(f"chk.send({text!r})\n")
                    else :
                        out.write(f"chk.expect({text!r})\n")
                else :
                    self.script.back()
                    break
            out.write("chk.exit()\n")
    def do_end (self) :
        priv = self.test_dir.relative_to(pathlib.Path().absolute())
        argv = ["firejail", "--quiet", f"--private={priv}", "--allow-debuggers"]
        if self.run_timeout is not None :
            argv.append(self.run_timeout)
        argv.extend(["/bin/bash", str(self.test_sh.name)])
        try :
            subprocess.run(argv)
        except Exception as err :
            print(err)
        if self.expect_io is not None :
            pass #TODO: read IO from expect
        report = self.test_dir.with_suffix(".zip")
        with report.open("wb") as out :
            with zipfile.ZipFile(out, "w",
                                 compression=zipfile.ZIP_LZMA,
                                 compresslevel=9) as zf :
                self.lang.report(zf)
                zf.write(self.test_sh, "test.sh")
                zf.writestr("tests.json", json.dumps(self.report))
