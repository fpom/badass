import json, datetime
from shlex import quote
from pathlib import Path
from hadlib import getopt

from .. import BaseLanguage
from ... import tree
from .drmem import parse as drparse

class Language (BaseLanguage) :
    SUFFIX = ".c"
    NAMES = ["C", "C11"]
    DESCRIPTION = "C11 (ISO/IEC 9899:2011)"
    def build (self, script, source) :
        self.log = []
        self.obj = []
        self.src = []
        now = datetime.datetime.now()
        self.date = now.strftime("%Y-%m-%d")
        self.time = now.strftime("%H:%M:%S.%f")
        # compile sources
        lflags = set()
        for path in source :
            self.src.append(path)
            if not path.match("*.c") :
                continue
            out, err, ret = self._mktmp(path.name)
            cf, lf = getopt([path], "linux", "gcc")
            lflags.update(lf)
            self.obj.append(path.with_suffix(".o"))
            gcc = (f"gcc -c"
                   f" -g -fno-inline -fno-omit-frame-pointer -Wall -std=c11 -Wpedantic"
                   f" {' '.join(cf)} {quote(str(self[path]))} -o {self[self.obj[-1]]}")
            self.log.append(["compile", self[path], gcc,
                             tree(stdout=out, stderr=err, exit_code=ret)])
            script.write(
                f"rm -f {self[self.obj[-1]]}\n"
                f"{gcc} > {self[out]} 2> {self[err]}\n"
                f"echo $? > {self[ret]}\n")
        # link objects
        out, err, ret = self._mktmp("a.out")
        gcc = " ".join(["gcc",
                        " ".join(f"{quote(str(self[o]))}" for o in self.obj),
                        " ".join(lflags)])
        self.log.append(["link", Path("a.out"), gcc,
                         tree(stdout=out, stderr=err, exit_code=ret)])
        script.write(f"rm -f a.out\n"
                     f"{gcc} > {self[out]} 2> {self[err]}\n"
                     f"echo $? > {self[ret]}\n")
    def run (self, script, stdio=None, memchk=True) :
        if memchk :
            self.mem = self._mkdtemp(prefix="mem-")
            drmem = (f"drmemory -quiet -logdir {self[self.mem]}"
                     " -callstack_srcfile_prefix $(pwd) --")
        else :
            self.mem = None
            drmem = ""
        out, err, ret = self._mktmp("run")
        if stdio is not None :
            in_ = self._mktmp("run", ".in")
            ioprog = f"{stdio} --stdout={self[out]} --stdin={self[in_]}"
            stdin = ""
            stdout = ""
        else :
            self.log.append(["run", Path("a.out"), "a.out",
                             tree(stdout=out, stderr=err, exit_code=ret)])
            ioprog = ""
            stdin = "< /dev/null"
            stdout = f"> {self[out]}"
        script.write(f"{ioprog} {drmem} ./a.out {stdout} 2> {self[err]} {stdin}\n"
                     f"echo $? > {self[ret]}\n")
        if stdio is not None :
            return tree(stdin=in_, stdout=out, stderr=err, exit_code=ret)
    def report (self, archive=None) :
        report = tree(date=self.date,
                      time=self.time,
                      events=[])
        for action, path, cmd, stdio in self.log :
            retcode = stdio.exit_code.read_text(encoding="utf-8").strip()
            details = [f"`$ {cmd}` (returned {retcode})"]
            output = False
            for key, src in stdio.items() :
                if key.startswith("std") :
                    txt = src.read_text(encoding="utf-8").rstrip()
                    if txt :
                        details.append(f"\n\n**{key}:**\n\n```\n{txt}\n```")
                        if key != "stdin" :
                            output = True
            if retcode != "0" :
                stat = "fail"
            elif action in ("compile", "link") and output :
                stat = "warn"
            else :
                stat = "pass"
            report.events.append(tree(title=action,
                                      text=f"`{path}`",
                                      details="".join(details),
                                      status=stat))
        if self.mem is not None :
            self.memchk = tree()
            for path in self.mem.glob("DrMemory*/results.txt") :
                res = drparse(path)
                self.memchk[res.pid] = res
        if archive is not None :
            for path in self.src :
                archive.write(path, Path("src") / self[path])
            for action, path, _, stdio in self.log :
                for key, src in stdio.items() :
                    if key.startswith("std") :
                        archive.write(src, Path(action) / path / f"{key}.log")
            if self.mem is not None :
                memchk = Path("memchk")
                archive.write(self.mem, memchk)
                for path in self.mem.glob("DrMemory-*/*") :
                    archive.write(path, memchk / path.relative_to(self.mem))
                archive.writestr("memchk.json", json.dumps(self.memchk))
            archive.writestr("build-run.json", json.dumps(report))
    def prepare (self, code, out, source) :
        raise NotImplementedError()
