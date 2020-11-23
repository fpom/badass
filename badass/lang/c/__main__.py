import argparse, subprocess, tempfile, os
from pathlib import Path
from . import build

parser = argparse.ArgumentParser("badass.lang.c.build")
parser.add_argument("-s", "--script", default=None, type=str,
                    help="where to write build script")
parser.add_argument("-c", "--chdir", default=".", type=str,
                    help="change work directory before to proceed")
parser.add_argument("-q", "--quiet", default=False, action="store_true",
                    help="no not print commands before they are executed")
parser.add_argument("-p", "--prog", default=False, action="store_true",
                    help="print build program even if quiet")
parser.add_argument("source", nargs="+", type=str,
                    help="source files to compile")

args = parser.parse_args()

os.chdir(args.chdir)

if args.script is None :
    script = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".sh")
else :
    script = open(args.script, "w", encoding="utf-8")

source = [str(Path(p).relative_to(args.chdir)) for p in args.source]

if not args.quiet :
    script.write("set -x\n")

prog = Path(build(source, script))
script.flush()
subprocess.call(["bash", script.name])
if not args.quiet or args.prog :
    if prog.exists() :
        print(Path(args.chdir) / prog)
    else :
        print("build failed")
