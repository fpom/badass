from pathlib import Path
from hadlib import getopt

def build (source, script) :
    lflags = set()
    obj = []
    for path in (Path(p) for p in source) :
        if not path.match("*.c") :
            continue
        log = Path("build-" + path.name).with_suffix("")
        cf, lf = getopt([path], "linux", "gcc")
        lflags.update(lf)
        cf = " ".join(cf)
        obj.append(path.with_suffix(".o"))
        script.write(
            f"rm -f {obj[-1]}\n"
            f"gcc -c"
            f" -g -fno-inline -fno-omit-frame-pointer -Wall -std=c11 -Wpedantic {cf}"
            f" '{path}' -o {obj[-1]}"
            f" > {log}.stdout"
            f" 2> {log}.stderr\n"
            f"echo $? > {log}.ret\n")
    lflags = " ".join(lflags)
    objects = " ".join(f"'{o}'" for o in obj)
    script.write(f"rm -f a.out\n")
    script.write(f"gcc {objects} {lflags} > build.stdout 2> build.stderr\n"
                 f"echo $? > build.ret\n")
    return "a.out"
