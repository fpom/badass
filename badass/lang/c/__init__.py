import os, zipfile, json, datetime
from functools import wraps
from tempfile import mkstemp, mkdtemp
from shutil import rmtree
from shlex import quote
from pathlib import Path
from hadlib import getopt

from .drmem import parse as drparse

NAMES = ["C", "C11"]
DESCRIPTION = "C11 (ISO/IEC 9899:2011)"

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
def _mktmp (tmp, n=3) :
    trio = []
    for i in range(n) :
        fd, path = mkstemp(dir=tmp)
        os.close(fd)
        trio.append(Path(path).relative_to(_cwd))
    if n == 1 :
        return trio[0]
    else :
        return tuple(trio)

@chdir
def build (source, script) :
    lflags = set()
    tmp = Path(mkdtemp(dir=str(_cwd)))
    now = datetime.datetime.now()
    trace = {"get" : [],
             "log" : [],
             "obj" : [],
             "src" : [],
             "tmp" : tmp,
             "date" : now.strftime("%Y-%m-%d"),
             "time" : now.strftime("%H:%M:%S.%f")}
    for path in (Path(p) for p in source) :
        if not path.match("*.c") :
            continue
        trace["src"].append(path)
        out, err, ret = _mktmp(tmp)
        trace["get"].extend([out, err, ret])
        cf, lf = getopt([path], "linux", "gcc")
        lflags.update(lf)
        trace["obj"].append(path.with_suffix(".o"))
        gcc = (f"gcc -c"
               f" -g -fno-inline -fno-omit-frame-pointer -Wall -std=c11 -Wpedantic"
               f" {' '.join(cf)} {quote(str(path))} -o {trace['obj'][-1]}")
        trace["log"].append(["compile", path, gcc, out, err, ret])
        script.write(
            f"rm -f {trace['obj'][-1]}\n"
            f"{gcc} > {out} 2> {err}\n"
            f"echo $? > {ret}\n")
    out, err, ret = _mktmp(tmp)
    trace["get"].extend([out, err, ret])
    gcc = " ".join(["gcc",
                    " ".join(f"{quote(str(o))}" for o in trace['obj']),
                    " ".join(lflags)])
    trace["log"].append(["link", Path("a.out"), gcc, out, err, ret])
    script.write(f"rm -f a.out\n"
                 f"{gcc} > {out} 2> {err}\n"
                 f"echo $? > {ret}\n")
    return trace

@chdir
def run (trace, script, stdout=True, stderr=True, memchk=True) :
    tmp = trace["tmp"]
    if memchk :
        mem = trace["mem"] = Path(mkdtemp(dir=tmp)).relative_to(_cwd)
        drmem = f"drmemory -quiet -logdir {mem} -callstack_srcfile_prefix {_cwd} --"
        trace["get"].append(mem)
    else :
        drmem = ""
    out, err, ret = _mktmp(tmp)
    if stdout :
        stdout = ""
        trace["out"] = out
    else :
        stdout = f"> {out}"
    if stderr :
        stderr = ""
        trace["err"] = err
    else :
        stderr = f"2> {err}"
    script.write(f"{drmem} a.out {stdout} {stderr} < /dev/null\n"
                 f"echo $? > {ret}")
    trace["log"].append(["run", Path("a.out"), "a.out < /dev/null", out, err, ret])
    trace["get"].extend([out, err, ret])

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
def report (trace, keep=None) :
    mem = trace["mem"]
    memchk = trace["memchk"] = {}
    for resfile in mem.glob("resfile.*") :
        path = Path(resfile.read_text(encoding="utf-8")).relative_to(_cwd)
        res = drparse(path, trace["src"], _cwd)
        memchk[res["pid"]] = res
    report = {"date" : trace["date"],
              "time" : trace["time"],
              "events" : []}
    for action, path, cmd, out, err, ret in trace["log"] :
        retcode = ret.read_text(encoding="utf-8").strip()
        stdout = out.read_text(encoding="utf-8").rstrip()
        stderr = err.read_text(encoding="utf-8").rstrip()
        if retcode != "0" :
            stat = "fail"
        elif action in ("compile", "link") and (stdout or stderr) :
            stat = "warn"
        else :
            stat = "pass"
        details = [f"`$ {cmd}` (returned {retcode})"]
        if stdout:
            details.append(f"\n\n**stdout:**\n\n```\n{stdout}\n```")
        if stderr:
            details.append(f"\n\n**stderr:**\n\n```\n{stderr}\n```")
        report["events"].append({"title" : action,
                                 "text" : f"`{path}`",
                                 "details" : "".join(details),
                                 "status" : stat})
    if keep :
        with zipfile.ZipFile(keep, "w",
                             compression=zipfile.ZIP_LZMA,
                             compresslevel=9) as zf :
            for path in trace["src"] :
                zf.write(path, Path("src") / path)
            for action, path, _, out, err, _ in trace["log"] :
                target = Path(action) / path / "stdout.log"
                zf.write(out, target)
                target = Path(action) / path / "stderr.log"
                zf.write(err, target)
            if "mem" in trace :
                mem = trace["mem"]
                memchk = Path("memchk")
                zf.write(mem, memchk)
                for path in mem.glob("DrMemory-*/*") :
                    zf.write(path, memchk / path.relative_to(mem))
            zf.writestr("report.json", json.dumps(report))
            zf.writestr("trace.json", json.dumps(trace, default=str))
