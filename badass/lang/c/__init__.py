import io, json, sys

from shlex import quote
from hadlib import getopt

from .. import BaseLanguage
from ... import tree, encoding, cached_property, mdesc
from .drmem import parse as drparse
from .srcio import Source

class Language (BaseLanguage) :
    SUFFIX = ".c"
    NAMES = ["C", "C11"]
    DESCRIPTION = "C11 (ISO/IEC 9899:2011)"
    MACROS = {"LoopStmt" : ("ForStmt", "WhileStmt", "DoStmt"),
              "CondStmt" : ("IfStmt", "SwitchStmt")}
    IGNORE = {"ISO C does not support the 'm' scanf flag"}
    def __init__ (self, test) :
        super().__init__(test)
        self.log = []
        self.mem = self.test.log_dir / "memchk"
        self.mem.mkdir(parents=True, exist_ok=True)
    @cached_property
    def source (self) :
        return Source(self.test.test_dir, self.test.source_files)
    def add_source (self, source, path) :
        self.source.add(source, path)
    def del_source (self, name) :
        self.source.discard(name)
    def decl (self, sig, decl=None) :
        return self.source.decl(sig, decl)
    def __getitem__ (self, path) :
        try :
            path = path.relative_to(self.test.test_dir)
        except :
            pass
        return quote(str(path))
    def make_script (self, path) :
        with path.open("w", **encoding) as script :
            for sub in ("build", "run", "memchk") :
                script.write(f"mkdir -p {self[self.test.log_dir / sub]}\n")
            self.pid = self.test.add_path(name="make.pid", log="build")
            script.write(f"echo $$ > {self[self.pid]}\n")
            self.env = self.test.add_path(name="make.env", log="build")
            script.write(f"env > {self[self.env]}\n"
                         f"echo '######' >> {self[self.env]}\n"
                         f"echo GCC=$(which gcc) >> {self[self.env]}\n"
                         f"echo GCC_VERSION=$(gcc --version) >> {self[self.env]}\n"
                         f"echo DRMEMORY=$(which drmemory) >> {self[self.env]}\n")
            # compile sources
            lflags = set()
            obj_files = []
            for path in self.source  :
                if not path.match("*.c") :
                    continue
                base = "-".join(path.parts)
                out = self.test.add_path(name=f"{base}.stdout", log="build")
                err = self.test.add_path(name=f"{base}.stderr", log="build")
                ret = self.test.add_path(name=f"{base}.status", log="build")
                obj = path.with_suffix(".o")
                obj_files.append(obj)
                cf, lf = getopt([self.test.test_dir / path], "linux", "gcc")
                lflags.update(lf)
                gcc = (f"gcc -c"
                       f" -g -fno-inline -fno-omit-frame-pointer -std=c11"
                       f" -Wall -Wpedantic"
                       f" {' '.join(cf)} {self[path]} -o {self[obj]}")
                script.write(f"rm -f {self[obj]}\n"
                             f"{gcc} -fdiagnostics-format=json > {self[out]} 2> {self[err]}\n"
                             f"echo $? > {self[ret]}\n")
                self.log.append(["compile", self[path], gcc,
                                 tree(stdout=out, stderr=err, exit_code=ret)])
            # link executable
            out = self.test.add_path(name=f"link.stdout", log="build")
            err = self.test.add_path(name=f"link.stderr", log="build")
            ret = self.test.add_path(name=f"link.status", log="build")
            obj = " ".join(self[o] for o in obj_files)
            gcc = f"gcc {obj} {' '.join(lflags)}"
            script.write(f"rm -f a.out\n"
                         f"{gcc} > {self[out]} 2> {self[err]}\n"
                         f"echo $? > {self[ret]}\n")
            self.log.append(["link", "a.out", gcc,
                             tree(stdout=out, stderr=err, exit_code=ret)])
            # run program
            drmem = (f"drmemory -quiet -logdir {self[self.mem]}"
                     " -callstack_srcfile_prefix $(pwd) --")
            err = self.test.add_path(name=f"run.stderr", log="run")
            ret = self._ret = self.test.add_path(name=f"run.status", log="run")
            script.write(f"{drmem} ./a.out 2> {self[err]}\n"
                         f"echo $? > {self[ret]}\n"
                         f"echo\n"
                         f"exit 0")
    @property
    def exit_code (self) :
        ret = self._ret.read_text(**encoding).strip()
        try :
            return int(ret)
        except :
            return ret
    def report_build (self) :
        for action, path, cmd, stdio in self.log :
            success = stdio.exit_code.read_text(**encoding).strip() == "0"
            info = []
            stderr = stdio.stderr.read_text(**encoding)
            try :
                diagnostics = json.loads(stderr)
            except :
                if stderr.strip() :
                    details = f"`$ {cmd}`\n<pre>\n{mdesc(stderr)}\n<pre>"
                else :
                    details = f"`$ {cmd}`"
                yield success, f"{action} `{path}`", details, None
                continue
            for diag in diagnostics :
                if diag["kind"] == "warning" and diag["message"] in self.IGNORE :
                    kind = "info"
                elif diag["kind"] not in ("info", "warning", "error") :
                    kind = "info"
                else :
                    kind = diag["kind"]
                pos = tree(line=sys.maxsize, path=None, col=sys.maxsize)
                for loc in diag["locations"] :
                    for key in ("start", "caret") :
                        if key in loc :
                            if loc[key]["line"] < pos.line :
                                pos = tree(line=loc[key]["line"],
                                           path=loc[key]["file"],
                                           col=loc[key]["column"])
                            elif loc[key]["line"] == pos.line :
                                pos.col = min(pos.col, loc[key]["column"])
                line = self.source[pos.path, pos.line-1]
                info.append((kind, diag["message"], pos,
                             line[:pos.col].decode(**encoding),
                             line[pos.col:].decode(**encoding)))
            yield success, f"{action} `{path}`", f"`$ {cmd}`", info
    def report_memchk (self) :
        memchk = {}
        for path in self.mem.glob("DrMemory*/results.txt") :
            res = drparse(path)
            memchk[res.pid] = res
        make_pid = int(self.pid.read_text(**encoding))
        for pid, res in sorted(memchk.items()) :
            for num, info in sorted(res.errors.items()) :
                details = io.StringIO()
                details.write(f"process {pid} (child of {make_pid}), call stack:\n\n")
                for n, frame in enumerate(info.stack) :
                    details.write(f" {n+1}. function `{frame.function}`"
                                  f" (file `{frame.path}`, line `{frame.line}`)\n")
                yield True, f"{mdesc(info.description)}", details.getvalue(), None
