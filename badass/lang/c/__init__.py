import io

from shlex import quote
from hadlib import getopt

from .. import BaseLanguage
from ... import tree, encoding, cached_property, mdesc
from ...run import PASS, WARN, FAIL
from .drmem import parse as drparse
from .srcio import Source

class Language (BaseLanguage) :
    SUFFIX = ".c"
    NAMES = ["C", "C11"]
    DESCRIPTION = "C11 (ISO/IEC 9899:2011)"
    MACROS = {"LoopStmt" : ("ForStmt", "WhileStmt", "DoStmt"),
              "CondStmt" : ("IfStmt", "SwitchStmt")}
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
    def decl (self, signature) :
        return self.source.decl(signature)
    def __getitem__ (self, path) :
        try :
            path = path.relative_to(self.test.test_dir)
        except :
            pass
        return quote(str(path))
    def make_script (self, path) :
        with path.open("w", **encoding) as script :
            self.pid = self.test.add_path(name=f"make.pid", log="build")
            script.write(f"echo $$ > {self[self.pid]}\n")
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
                             f"{gcc} > {self[out]} 2> {self[err]}\n"
                             f"echo $? > {self[ret]}\n")
                self.log.append(["compile", self[path], gcc,
                                 tree(stdout=out, stderr=err, exit_code=ret)])
            # link executable
            out = self.test.add_path(name=f"link.stdout", log="build")
            err = self.test.add_path(name=f"link.stderr", log="build")
            ret = self.test.add_path(name=f"link.status", log="build")
            obj = " ".join(self[o] for o in obj_files)
            gcc = f"gcc {' '.join(lflags)} {obj}"
            script.write(f"rm -f a.out\n"
                         f"{gcc} > {self[out]} 2> {self[err]}\n"
                         f"echo $? > {self[ret]}\n")
            self.log.append(["link", "a.out", gcc,
                             tree(stdout=out, stderr=err, exit_code=ret)])
            # run program
            drmem = (f"drmemory -quiet -logdir {self[self.mem]}"
                     " -callstack_srcfile_prefix $(pwd) --")
            err = self.test.add_path(name=f"run.stderr", log="run")
            ret = self.test.add_path(name=f"run.status", log="run")
            script.write(f"{drmem} ./a.out 2> {self[err]}\n"
                         f"echo $? > {self[ret]}\n"
                         f"exit 0")
    def report_build (self) :
        for action, path, cmd, stdio in self.log :
            retcode = stdio.exit_code.read_text(encoding="utf-8").strip()
            details = io.StringIO()
            details.write(f"`$ {cmd}`\\\n(returned {retcode})")
            output = False
            for key in ("stdout", "stderr") :
                txt = stdio[key].read_text(**encoding).rstrip()
                if txt :
                    details.write(f"\n\n**{key}:**\n\n```\n{txt}\n```")
                    output = True
            if retcode != "0" :
                stat = FAIL
            elif action in ("compile", "link") and output :
                stat = WARN
            else :
                stat = PASS
                details = io.StringIO()
            yield stat, f"{action} `{path}`", details.getvalue()
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
                yield WARN, f"{mdesc(info.description)}", details.getvalue()
