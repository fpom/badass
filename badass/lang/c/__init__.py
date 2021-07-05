import io, json, sys

from hadlib import getopt

from .. import BaseLanguage
from ... import tree, encoding, cached_property, mdesc
from .drmem import parse as drparse
from .strace import STrace
from .srcio import Source, ASTPrinter

class Language (BaseLanguage) :
    SUFFIX = ".c"
    NAMES = ["C", "C11"]
    DESCRIPTION = "C11 (ISO/IEC 9899:2011)"
    MACROS = {"LoopStmt" : ("ForStmt", "WhileStmt", "DoStmt"),
              "CondStmt" : ("IfStmt", "SwitchStmt")}
    IGNORE = {"ISO C does not support the 'm' scanf flag"}
    def __init__ (self, test) :
        super().__init__(test)
        self.dir = self.test.test_dir
        self.log = []
    @cached_property
    def source (self) :
        return Source(self.test.test_dir/ "src")
    def add_source (self, source, path) :
        self.source.add(source, path)
    def del_source (self, name) :
        self.source.discard(name)
    def decl (self, sig, decl=None) :
        return self.source.decl(sig, decl)
    def make_script (self, trace="drmem") :
        make_path = self.dir / "make.sh"
        with make_path.open("w", **encoding) as script :
            for sub in ("build", "run", "memchk", "strace") :
                script.write(f"mkdir -p log/{sub}\n")
            script.write(f"echo $$ > log/build/make.pid\n"
                         f"env > log/build/make.env\n"
                         f"echo '######' >> log/build/make.env\n"
                         f"echo GCC=$(which gcc) >> log/build/make.env\n"
                         f"echo GCC_VERSION=$(gcc --version) >> log/build/make.env\n"
                         f"echo DRMEMORY=$(which drmemory) >> log/build/make.env\n")
            # compile sources
            lflags = set()
            obj_files = []
            for path in self.source  :
                if not path.match("*.c") :
                    continue
                base = "-".join(path.parts)
                out = f"log/build/{base}.stdout"
                err = f"log/build/{base}.stderr"
                ret = f"log/build/{base}.status"
                obj = path.with_suffix(".o")
                obj_files.append(str(obj))
                cf, lf = getopt([self.dir / "src" / path], "linux", "gcc")
                lflags.update(lf)
                gcc = (f"gcc -c"
                       f" -g -fno-inline -fno-omit-frame-pointer -std=c11"
                       f" -Wall -Wpedantic"
                       f" {' '.join(cf)}"
                       f" {path}"
                       f" -o {obj}")
                script.write(f"rm -f {obj}\n"
                             # put -fdiagnostics-format=json here
                             # to hide it from user-visible logs
                             f"(cd src ; {gcc} -fdiagnostics-format=json)"
                             f" > {out} 2> {err}\n"
                             f"echo $? > {ret}\n")
                self.log.append(["compile", path, gcc,
                                 tree(stdout=out, stderr=err, exit_code=ret)])
            # link executable
            out = "log/build/link.stdout"
            err = "log/build/link.stderr"
            ret = "log/build/link.status"
            gcc = f"gcc {' '.join(obj_files)} {' '.join(lflags)}"
            script.write(f"rm -f src/a.out\n"
                         f"(cd src ; {gcc}) > {out} 2> {err}\n"
                         f"echo $? > {ret}\n")
            self.log.append(["link", "a.out", gcc,
                             tree(stdout=out, stderr=err, exit_code=ret)])
            # run program
            if trace == "drmem" :
                trace = (f"drmemory -quiet -logdir log/memchk"
                         " -callstack_srcfile_prefix $(pwd) --")
            elif trace == "strace" :
                trace = f"strace -r -ff -xx -v -o log/strace/log"
            else :
                raise ValueError(f"unknown tracing method '{trace}'")
            err = "log/run/run.stderr"
            ret = "log/run/run.status"
            script.write(f"{trace} ./src/a.out 2> {err}\n"
                         f"echo $? > {ret}\n"
                         f"echo\n"
                         f"exit 0")
        return make_path, None
    @property
    def exit_code (self) :
        ret = (self.dir / "log/run/run.status").read_text(**encoding).strip()
        try :
            return int(ret)
        except :
            return ret
    def checks (self) :
        yield "compile and link", "build", list(self.report_build())
        checks = list(self.report_memchk())
        if checks :
            yield "memory safety checks", "memchk", checks
    def strace (self) :
        return STrace(self.dir / "log/strace")
    def report_build (self) :
        for action, path, cmd, stdio in self.log :
            success = (self.dir / stdio.exit_code).read_text(**encoding).strip() == "0"
            info = []
            stderr = (self.dir / stdio.stderr).read_text(**encoding)
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
        for path in (self.dir / "log/memchk").glob("DrMemory*/results.txt") :
            res = drparse(path)
            memchk[res.pid] = res
        make_pid = int((self.dir / "log/build/make.pid").read_text(**encoding))
        for pid, res in sorted(memchk.items()) :
            for num, info in sorted(res.errors.items()) :
                details = io.StringIO()
                details.write(f"process {pid} (child of {make_pid}), call stack:\n\n")
                for n, frame in enumerate(info.stack) :
                    details.write(f" {n+1}. function `{frame.function}`"
                                  f" (file `{frame.path}`, line `{frame.line}`)\n")
                yield True, f"{mdesc(info.description)}", details.getvalue(), None
