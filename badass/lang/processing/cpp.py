import subprocess

_cpp_cmd = {"#include" : "//##INCLUDE##",
            "#define" : "//##DEFINE##",
            "#ifdef" : "//##IFDEF##",
            "#ifndef" : "//##IFNDEF##",
            "#endif" : "//##ENDIF##"}

_cpp_head = ""

def esc (src) :
    for cmd, esc in _cpp_cmd.items() :
        src = src.replace(cmd, esc)
    return src

def unesc (src) :
    for cmd, esc in _cpp_cmd.items() :
        src = src.replace(esc, cmd)
    return src


def cpp (src, env={}, **var) :
    _env = dict(env)
    _env.update(var)
    out = subprocess.run(["cpp", "-P"] + [f"-D{k}={v}" for k, v in _env.items()],
                         input=esc(src),
                         encoding="utf-8",
                         capture_output=True).stdout
    return unesc(out.replace(_cpp_head, ""))

_cpp_head = cpp("")
