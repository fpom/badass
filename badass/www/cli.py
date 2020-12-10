import argparse, sys, pathlib, subprocess, os

def add_arguments (sub) :
    excl = sub.add_mutually_exclusive_group(required=True)
    #
    excl.add_argument("-f", "--form", metavar="YAML",
                       type=argparse.FileType(mode="r", encoding="utf-8"),
                       help="generate form from YAML")
    group = sub.add_argument_group("form generation options")
    group.add_argument("-o", "--output", metavar="PATH",
                       type=argparse.FileType(mode="w", encoding="utf-8"),
                       default=sys.stdout,
                       help="output to PATH (default: stdout)")
    #
    excl.add_argument("-i", "--init", default=None, const=".", nargs="?", metavar="PATH",
                      help="copy static files to directory PATH (default: .)")
    group = sub.add_argument_group("static files init options")
    group.add_argument("-c", "--clobber", default=False, action="store_true",
                       help="replace existing files")
    #
    excl.add_argument("-p", "--passwd", type=str, metavar="CSV",
                      help="password CSV database")
    group = sub.add_argument_group("passwords management options")
    group.add_argument("-u", "--user", default=[], action="append", type=str,
                       help="(re)generate password for selected user (default: all)")
    group.add_argument("-r", "--read", default=False, action="store_true",
                       help="read passwords interactively instead of generating them")
    group.add_argument("-d", "--default", default=None, action="store", type=str,
                       help="password to be used (dangerous)")
    group.add_argument("-l", "--log", default=sys.stdout,
                       type=argparse.FileType(mode="w", encoding="utf-8"),
                       help="log changed password to LOG (default: stdout)")
    #
    excl.add_argument("-s", "--serve", default=False, action="store_true",
                       help="start Flask server")
    group = sub.add_argument_group("Flask options")
    group.add_argument("--no-pin", default=False, action="store_true",
                       help="disable online debugger PIN")
    group.add_argument("--env", default="development", type=str,
                       help="Flask environ (default: development)")
    group.add_argument("--reload", default=False, action="store_true",
                       help="enable Flask auto reload")

def main (args) :
    "www server and utilities"
    if args.form is not None :
        from .genform import Loader
        loader = Loader()
        form = loader.load(args.form)
        form(args.output)
    elif args.init is not None :
        from . import copy_static
        copy_static(pathlib.Path(args.init), args.clobber)
    elif args.passwd is not None :
        from .mkpass import mkpass
        mkpass(args.passwd, args.user or None, args.read, args.default, args.log)
    elif args.serve :
        env = dict(os.environ)
        env["FLASK_APP"] = "badass.www.server"
        env["FLASK_ENV"] = args.env
        if args.no_pin :
            env["WERKZEUG_DEBUG_PIN"] = "off"
        argv = ["flask", "run"]
        if not args.reload :
            argv.append("--no-reload")
        subprocess.run(argv, env=env)
    else :
        raise RuntimeError("unreachable code has been reached")
