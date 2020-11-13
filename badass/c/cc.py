import os, pathlib, shutil, sys, fnmatch, tempfile, subprocess

def which (name) :
    me = [pathlib.Path(__file__).resolve(),
          pathlib.Path(sys.argv[0]).resolve()]
    for path in os.get_exec_path() :
        p = shutil.which(name, path=path)
        if p is not None and pathlib.Path(p).absolute() not in me :
            return p

PATH = which("gcc")

class GCC (object) :
    opt0 = {("-o", "*"), "-static", "-static-*", "-std=*"}
    opt1 = {"-std=c11", "-Wpedantic", "-Wall"}
    opt2 = {("-l", "dmalloc")}
    def __init__ (self) :
        self.path = which("gcc")
    def _match1 (self, pattern, args) :
        if isinstance(pattern, tuple) :
            opt, glob = pattern
            if len(args) > 1 and args[0] == opt and fnmatch.fnmatch(args[1], glob) :
                return 2
            elif args and fnmatch.fnmatch(args[0], opt + glob) :
                return 1
        elif args and fnmatch.fnmatch(args[0], pattern) :
            return 1
        else :
            return 0
    def _match (self, options, source, target, cp=False) :
        for opt in options :
            m = self._match1(opt, source)
            if m :
                if cp :
                    options.discard(opt)
                    target.extend(source[:m])
                del source[:m]
                return m
        return 0
    def _patch (self, path, tmp) :
        head, tail = [], []
        for line in open(path) :
            tail.append(line.rstrip())
            if line.strip().startswith("#include") :
                head.extend(tail)
                del tail[:]
        head.append("#include <dmalloc.h>")
        fid, tgt = tempfile.mkstemp(suffix=".c",
                                    prefix=pathlib.Path(path).name,
                                    dir=tmp,
                                    text=True)
        with os.fdopen(fid, mode="w") as out :
            if head :
                out.write("\n".join(head))
                out.write("\n")
            if tail :
                out.write("\n".join(tail))
                out.write("\n")
        return tgt
    def __call__ (self, args) :
        with tempfile.TemporaryDirectory() as tmp :
            args = list(args)
            argv = ["gcc"]
            options = set(self.opt1)
            first = True
            while args :
                if self._match(self.opt0, args, argv) :
                    continue
                elif self._match(options, args, argv, cp=True) :
                    continue
                elif os.path.isfile(args[0]) :
                    if first :
                        argv.extend("".join(opt) for opt in options)
                        options = set(self.opt2)
                        first = False
                    argv.append(self._patch(args.pop(0), tmp))
                else :
                    argv.append(args.pop(0))
            argv.extend("".join(opt) for opt in options)
            proc = subprocess.run(argv, stdin=subprocess.DEVNULL)
            return proc.returncode

gcc = GCC()

if __name__ == "__main__" :
    sys.exit(gcc(sys.argv[1:]))
