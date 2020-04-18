from pathlib import Path
from subprocess import Popen, PIPE, STDOUT
from tempfile import NamedTemporaryFile
from collections import namedtuple
import pandas as pd

class SEvent (object) :
    def __init__ (self, pid, time, kind, **info) :
        self.pid = pid
        self.time = time
        self.kind = kind
        self._info = info
        for key, val in info.items() :
            setattr(self, key, val)
    def __repr__ (self) :
        return (f"{self.__class__.__name__}({self.pid}, {self.time:f}, {self.kind!r}, "
                + ", ".join(f"{k}={v!r}" for k, v in self._info.items()))

call = namedtuple("call", ["pid", "time", "head", "resume"])

class STrace (object) :
    def __init__ (self) :
        self.pids = {}
        self.root = None
    @classmethod
    def parse (cls, lines) :
        self = cls()
        started = {}
        for pid, time, info in (l.strip().split(None, 2) for l in lines
                                if not l.endswith("+++")) :
            if info.endswith("<unfinished ...>") :
                name = info.split("(", 1)[0]
                started[pid] = call(pid, time, info[:-16], f"<... {name} resumed>")
                continue
            elif pid in started :
                assert info.startswith(started[pid].resume), "wrong resume"
                start = started.pop(pid)
                time, info = start.time, start.head + info[len(start.resume):]
            pid, time = int(pid), float(time)
            if self.root is None :
                self.root = pid
            if pid not in self.pids :
                self.pids[pid] = []
            if info.startswith("+++") :
                self.pids[pid].append(SEvent(pid, time, "exit",
                                             code=int(info.split()[3])))
            elif info.startswith("---") :
                info = info.strip("- ")
                sig, info = info.split(None, 1)
                params = dict(x.split("=", 1) for x in info.strip("{}").split(", "))
                self.pids[pid].append(SEvent(pid, time, "signal",
                                             name=sig,
                                             params=params))
            else :
                name = info.split("(", 1)[0]
                params, ret = info[len(name):].rsplit("=", 1)
                self.pids[pid].append(SEvent(pid, time, "call",
                                        name=name.strip(),
                                        params=params.strip(),
                                        ret=ret.strip()))
        return self

class OneAss (object) :
    def __init__ (self, *files) :
        self.files = [Path(f) for f in files]
    def __call__ (self, path) :
        path = Path(path)
        script = (["cp -f '{}' .".format(p.absolute()) for p in self.files
                   if p.name != "build.sh" or not (path / "build.sh").exists()]
                  + ["sh build.sh >build.out 2>build.err",
                     "echo $? > build.ret",
                     "strace -f -r -o run.sys ./a.out >run.out 2>run.err",
                     "echo $? > run.ret",
                     "touch run.ass run.sys",
                     "set -x",
                     "cat build.ret",
                     "cat build.out",
                     "cat build.err",
                     "cat run.ret",
                     "cat run.out",
                     "cat run.err",
                     "cat run.ass",
                     "cat run.sys"])
        with NamedTemporaryFile(mode="w", dir=path, suffix=".sh") as tmp :
            tmp.write("\n".join(script) + "\n")
            tmp.flush()
            proc = Popen(["firejail",
                          "--quiet",
                          "--overlay-tmpfs",
                          "--allow-debuggers",
                          "sh", tmp.name],
                         cwd=path,
                         stdout=PIPE,
                         stderr=STDOUT,
                         encoding="utf-8")
            proc.wait()
        run = {}
        buf = run["out+err"] = []
        for line in (l.rstrip() for l in proc.stdout) :
            if line.startswith("+ cat ") :
                buf = run[line.split()[-1]] = []
            else :
                buf.append(line)
        for key, val in run.items() :
            if key == "run.ass" :
                log = {}
                for line in val :
                    ret, tag, test = line[2:-2].split(":", 2)
                    log[tag] = (ret, test)
                run[key] = log
            elif key.endswith(".out") or key.endswith(".err") or key == "out+err" :
                run[key] = "\n".join(val)
            elif key.endswith(".ret") :
                run[key] = int(val[0].strip())
            elif key.endswith(".sys") :
                run[key] = STrace.parse(val)
        return run

class GroupAss (object) :
    def __init__ (self, path,
                  morefiles=["badass.h"],
                  include=["*.c", "*.h", "build.sh", "Makefile"]) :
        self.path = Path(path)
        self.one = OneAss(*morefiles, *(p for g in include for p in self.path.glob(g)
                                        if p.is_file()))
    def __iter__ (self) :
        for path in self.path.glob("*") :
            if path.is_dir() :
                yield path.name, self.one(path)
    def save (self, path) :
        data = dict(self)
        df = pd.DataFrame(index=sorted(data))
        for name, assess in data.items() :
            for key, val in assess.items() :
                if key == "run.sys" :
                    continue
                elif key == "run.ass" :
                    for ass, (res, test) in val.items() :
                        if ass not in df.columns :
                            df[ass] = pd.Series(None, index=df.index, dtype=int)
                        if res == "passed" :
                            df.loc[name,ass] = 1
                        elif res == "failed" :
                            df.loc[name,ass] = 0
                else :
                    if key not in df.columns :
                        if key.endswith(".ret") :
                            df[key] = pd.Series(None, index=df.index, dtype=int)
                        else :
                            df[key] = pd.Series(None, index=df.index, dtype=str)
                    df.loc[name, key] = val
        df.to_csv(path)
