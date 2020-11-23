import os
from functools import wraps
from tempfile import mkstemp, mkdtemp
from shutil import rmtree
from shlex import quote
from pathlib import Path
from hadlib import getopt

_cwd = None

def chdir (fun) :
    @wraps(fun)
    def wrapper (*l, **k) :
        global _cwd
        if _cwd is None :
            _cwd = Path().absolute()
        return fun(*l, **k)
    return wrapper

@chdir
def _mk3tmp (tmp) :
    trio = []
    for i in range(3) :
        fd, path = mkstemp(dir=tmp)
        os.close(fd)
        trio.append(Path(path).relative_to(_cwd))
    return tuple(trio)

@chdir
def build (source, script) :
    lflags = set()
    tmp = Path(mkdtemp(dir=str(_cwd)))
    trace = {"get" : [],
             "log" : [],
             "obj" : [],
             "tmp" : tmp}
    for path in (Path(p) for p in source) :
        if not path.match("*.c") :
            continue
        out, err, ret = _mk3tmp(tmp)
        trace["get"].extend([out, err, ret])
        cf, lf = getopt([path], "linux", "gcc")
        lflags.update(lf)
        trace["obj"].append(path.with_suffix(".o"))
        gcc = (f"gcc -c"
               f" -g -fno-inline -fno-omit-frame-pointer -Wall -std=c11 -Wpedantic"
               f" {' '.join(cf)} {quote(str(path))} -o {trace['obj'][-1]}")
        trace["log"].append(["compiling", path, gcc, out, err, ret])
        script.write(
            f"rm -f {trace['obj'][-1]}\n"
            f"{gcc} > {out} 2> {err}\n"
            f"echo $? > {ret}\n")
    out, err, ret = _mk3tmp(tmp)
    trace["get"].extend([out, err, ret])
    gcc = " ".join(["gcc",
                    " ".join(f"{quote(str(o))}" for o in trace['obj']),
                    " ".join(lflags)])
    trace["log"].append(["linking", "a.out", gcc, out, err, ret])
    script.write(f"rm -f a.out\n"
                 f"{gcc} > {out} 2> {err}\n"
                 f"echo $? > {ret}\n")
    return trace

@chdir
def run (trace, script, stdio=False, memchk=True) :
    tmp = trace["tmp"]
    if memchk :
        mem = trace["mem"] = Path(mkdtemp(dir=tmp)).relative_to(_cwd)
        drmem = f"drmemory -quiet -logdir {mem} -callstack_srcfile_prefix {_cwd} -- "
        trace["get"].append(mem)
    else :
        drmem = ""
    out, err, ret = _mk3tmp(tmp)
    if stdio :
        script.write(f"{drmem}a.out > {out} 2> {err} < /dev/null\n"
                     f"echo $? > {ret}")
        trace["log"].append(["running", "a.out", "a.out < /dev/null", out, err, ret])
        trace["get"].extend([out, err, ret])
    else :
        trace["get"].extend([out, err, ret])
        script.write(f"{drmem}a.out\n"
                     f"echo $? > {ret}")

@chdir
def clear (trace) :
    errors = []
    def onerror (fun, path, exc) :
        errors.append((path, exc))
    rmtree(trace["tmp"], onerror=onerror)
    for path in trace["obj"] + [Path("a.out")] :
        try :
            path.unlink()
        except Exception as err :
            errors.append((path, err))
    return errors

@chdir
def report (trace) :
    pass
