import argparse, sys, pathlib, subprocess, os

class UserAction (argparse.Action) :
    def __call__ (self, parser, namespace, values, option_string) :
        print("***", self.dest, "=", values or True)
        setattr(namespace, self.dest, values or True)

def add_arguments (sub) :
    excl = sub.add_mutually_exclusive_group()
    #
    excl.add_argument("-f", "--form", metavar="YAML",
                       type=argparse.FileType(mode="r", encoding="utf-8"),
                       help="generate form from YAML")
    group = sub.add_argument_group("form generation options")
    group.add_argument("--output", metavar="PATH",
                       type=argparse.FileType(mode="w", encoding="utf-8"),
                       default=sys.stdout,
                       help="output to PATH (default: stdout)")
    #
    excl.add_argument("-i", "--init", default=None, const=".", nargs="?", metavar="PATH",
                      help="copy static files to directory PATH (default: .)")
    group = sub.add_argument_group("static files init options")
    group.add_argument("--clobber", default=False, action="store_true",
                       help="replace existing files")
    #
    excl.add_argument("-a", "--add-user", dest="dbpath", metavar="PATH", default=None,
                      help="add a new user to database stored in PATH")
    group = sub.add_argument_group("options to add user")
    group.add_argument("--email", metavar="EMAIL",
                       help="new user's email address")
    group.add_argument("--first-name", dest="firstname", metavar="NAME", default=None,
                       help="new user's first name")
    group.add_argument("--last-name", dest="lastname", metavar="NAME", default=None,
                       help="new user's last name (family name)")
    group_excl = group.add_mutually_exclusive_group()
    group_excl.add_argument("--group", metavar="GROUP", default=None,
                            help="new user's group")
    group_excl.add_argument("--no-group", dest="group", action="store_const", const="",
                            help="set new user with no group")
    studid_excl = group.add_mutually_exclusive_group()
    studid_excl.add_argument("--student-id", dest="studentid", metavar="NUM",
                             default=None,
                             help="new user's student number")
    studid_excl.add_argument("--no-student-id", dest="studentid",
                             action="store_const", const="",
                             help="set new user with no student number")
    group.add_argument("--password", metavar="PASSWORD", default=None,
                       help=("new user's password (WARNING: this will be visible"
                             " system-wide in process' argv)"))
    group.add_argument("--activated", default=None,
                       action=argparse.BooleanOptionalAction,
                       help="activate new user's account without requiring a login")
    role_excl = group.add_mutually_exclusive_group()
    role_excl.add_argument("--role", dest="roles", metavar="ROLE",
                           action="append",
                           help="new user's role (reuse option to add several)")
    role_excl.add_argument("--no-roles", dest="roles", action="store_const", const=[],
                           help="set new user with no roles")
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
    elif args.dbpath is not None :
        from . import add_user
        add_user(args)
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
        raise RuntimeError("unreachable code has been reached (LOL)")
