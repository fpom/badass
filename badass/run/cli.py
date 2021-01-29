import runpy, ast
import badass.run

def add_arguments (sub) :
    sub.add_argument("-k", "--keep", default=False, action="store_true",
                     help="do not remove files after building the archives")
    sub.add_argument("-t", "--timeout", default=10, type=int,
                     help="timeout for I/O with child process")
    sub.add_argument("-d", "--define", type=str, action="append", default=[],
                     metavar="NAME[=VALUE]",
                     help="pass NAME to the script (True if VALUE is omitted)")
    sub.add_argument("script", type=str,
                     help="path to script")
    sub.add_argument("project", type=str,
                     help="path to project")

def main (args) :
    "run assessment script"
    badass.run.CONFIG.update(args)
    for d in args.define :
        try :
            k, v = d.split("=", 1)
            try :
                badass.run.ARGS[k] = ast.litteral_eval(v)
            except :
                badass.run.ARGS[k] = v
        except :
            badass.run.ARGS[d] = True
    runpy.run_path(args.script)
    badass.run.report()
