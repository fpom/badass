from pathlib import Path
from subprocess import Popen, DEVNULL
from tempfile import NamedTemporaryFile
from collections import namedtuple

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
        for pid, time, info in (l.strip().split(None, 2) for l in lines) :
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

class AssRunner (object) :
    def __init__ (self, *files) :
        self.files = [Path(f) for f in files]
    def __call__ (self, path) :
        path = Path(path)
        script = (["cp -f '{}' .".format(p.absolute()) for p in self.files
                   if p.name != "build.sh" or not (path / "build.sh").exists()]
                  + ["sh prepare.sh >prep.out 2>prep.err",
                     "echo $? > prep.ret",
                     "sh build.sh >build.out 2>build.err",
                     "echo $? > build.ret",
                     "strace -f -r -o run.sys ./a.out >run.out 2>run.err </dev/null",
                     "echo $? > run.ret",
                     "touch run.ass run.sys",
                     "set -x",
                     "cat prep.ret",
                     "cat prep.out",
                     "cat prep.err",
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
                         stdout=DEVNULL,
                         stderr=DEVNULL,
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
