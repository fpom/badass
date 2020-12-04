import runpy
import badass.run

def add_arguments (sub) :
    sub.add_argument("-t", "--timeout", default=1, type=int,
                     help="timeout for I/O with child process")
    sub.add_argument("script", type=str,
                     help="path to script")
    sub.add_argument("project", type=str,
                     help="path to project")

def main (args) :
    "run assessment script"
    badass.run.CONFIG.update(args)
    runpy.run_path(args.script)
    badass.run.report()
