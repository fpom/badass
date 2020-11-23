import argparse, subprocess, tempfile, os
from pathlib import Path
import colorama
from . import build, run, clear

colorama.init()
CF = colorama.Fore
CS = colorama.Style

parser = argparse.ArgumentParser("badass.lang.c.build")
parser.add_argument("-s", "--script", default=None, type=str,
                    help="where to write build script")
parser.add_argument("-c", "--chdir", default=".", type=str,
                    help="change work directory before to proceed")
parser.add_argument("-l", "--logs", default=False, action="store_true",
                    help="show build logs")
parser.add_argument("-r", "--run", default=False, action="store_true",
                    help="run built program")
parser.add_argument("-k", "--keep", default=False, action="store_true",
                    help="keep temporary files")
parser.add_argument("source", nargs="+", type=str,
                    help="source files to compile")

args = parser.parse_args()
source = [str(Path(p).relative_to(args.chdir)) for p in args.source]

os.chdir(args.chdir)

if args.script is None :
    script = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".sh")
else :
    script = open(args.script, "w", encoding="utf-8")

trace = build(source, script)
if args.run :
    run(trace, script, stdio=True)
script.flush()

subprocess.call(["bash", script.name])

if args.logs :
    for action, path, cmd, out, err, ret in trace["log"] :
        ret = ret.read_text(encoding="utf-8").rstrip()
        if ret == "0" :
            ret = f"{CF.GREEN}{CS.BRIGHT}✔ {ret}{CS.RESET_ALL}"
        else :
            ret = f"{CF.RED}{CS.BRIGHT}✘ {ret}{CS.RESET_ALL}"
        print(f"{CF.BLUE}{CS.BRIGHT}{action}{CS.RESET_ALL} {path or ''} {ret}\n"
              f"{CF.WHITE}{CS.DIM}$ {cmd}{CS.RESET_ALL}")
        out = out.read_text(encoding="utf-8").rstrip()
        if out :
            print(f"{CF.YELLOW}{CS.DIM}{out}{CS.RESET_ALL}")
        err = err.read_text(encoding="utf-8").rstrip()
        if err :
            print(f"{CF.RED}{CS.DIM}{err}{CS.RESET_ALL}")

if not args.keep :
    errors = clear(trace)
    try :
        if args.script is not None :
            Path(script.name).unlink()
    except Exception as err :
        errors.append((script.name, err))
    for path, err in errors :
        print(f"{CF.RED}{CS.BRIGHT}could not unlink{CS.RESET_ALL} {path}"
              f" {CS.DIM}{err}{CS.RESET_ALL}")
