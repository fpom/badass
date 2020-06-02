import argparse, pathlib, importlib, sys, functools
import lxml.etree
from colorama import init as colorama_init, Fore, Style
from .db import DB

colorama_init()

def record (method) :
    @functools.wraps(method)
    def wrapper (self, args) :
        ret = method(self, args)
        if args.record :
            self.log.write(f"{Fore.BLUE}{Style.BRIGHT}save{Style.RESET_ALL}"
                           f" {args.record} in {args.db}\n")
            project, test = args.record.split(":", 1)
            db = DB(args.db)
            if method.__name__ == "do_run" :
                db.add_run(project, test, ret)
            else :
                db.add_check(project, test, ret)
        db.close()
        return ret
    return wrapper

class BadassCLI (object) :
    def __init__ (self, path, out, log) :
        self.path = pathlib.Path(path)
        self.out = out
        self.log = log
        self.mod = {}
        self.src = {}
    def __call__ (self, args) :
        cmd = getattr(self, "do_" + args.command)
        cmd(args)
    def _source_load (self, path, source=None) :
        self.log.write(f"{Fore.BLUE}{Style.BRIGHT}load{Style.RESET_ALL} {path}\n")
        path = (self.path / pathlib.Path(".//" + str(path))).relative_to(self.path)
        if path in self.src :
            return self.src[path]
        fmt = path.suffix.lstrip(".").lower()
        if fmt in self.mod :
            mod = self.mod[fmt]
        else :
            mod = self.mod[fmt] = importlib.import_module("." + fmt, "badass")
        src = self.src[path] = mod.source.Source(str(self.path / path), source)
        return src
    ##
    ## patch
    ##
    @record
    def do_patch (self, args) :
        base = self._source_load(args.path)
        for cmd, arg in zip(args.expr[::2], args.expr[1::2]) :
            getattr(self, "_do_patch_" + cmd)(base, arg)
        src = base.src()
        self.out.write(src)
        return src
    def _do_patch_del (self, base, name) :
        self.log.write(f" {Fore.RED}{Style.BRIGHT}---{Style.RESET_ALL} {name}\n")
        del base[name]
    def _do_patch_add (self, base, name_path) :
        name, path = name_path.split("@", 1)
        self.log.write(f" {Fore.GREEN}{Style.BRIGHT}+++{Style.RESET_ALL}"
                       f" {name}{Fore.WHITE}{Style.DIM}@{Style.RESET_ALL}{path}\n")
        code = self._source_load(path)
        base.add(code[name])
    ##
    ## xpath
    ##
    @record
    def do_xpath (self, args) :
        if not (args.source or args.xml or args.count) :
            args.source = True
        src = self._source_load(args.path)
        if args.source or args.xml :
            if args.source :
                ret = src(args.expr, "src")
            elif args.xml :
                ret = src(args.expr, "xml")
            if not isinstance(ret, list) :
                ret = [ret]
            if args.xml :
                for i, r in enumerate(ret) :
                    try :
                        ret[i] = lxml.etree.tostring(r, pretty_print=True,
                                                     encoding="utf-8")
                    except :
                        ret[i] = str(r)
            for i, r in enumerate(ret) :
                if i :
                    self.out.write("\n\n")
                if isinstance(r, bytes) :
                    ret[i] = r.decode("utf-8")
                elif not isinstance(r, str) :
                    ret[i] = str(r)
            val = "\n\n".join(r + "\n" for r in ret)
            self.out.write(val)
            return val
        elif args.count :
            ret = src(args.expr)
            if isinstance(ret, list) :
                self.out.write(f"{len(ret)}\n")
                return len(ret)
            elif ret is None :
                self.out.write("0\n")
                return 0
            else :
                self.out.write("1\n")
                return 1
    ##
    ## has
    ##
    @record
    def do_has (self, args) :
        patt, path = args.decl.split("@", 1)
        self._has = getattr(self, "_has", 0) + 1
        decl = self._source_load(f".{self._has}.c", patt + ";")
        name = next(iter(decl.d))
        code = self._source_load(path)
        if decl.sig(name) == name :
            found = name in code.d
        else :
            found = name in code.d and decl.sig(name) == code.sig(name)
        if found :
            patt = code.sig(name)
            path, line, _ = code.loc(name)
            self.log.write(f"{Fore.GREEN}{Style.BRIGHT}found{Style.RESET_ALL}"
                           f" {patt}{Fore.WHITE}{Style.DIM}@{Style.RESET_ALL}"
                           f"{path}:{line}\n")
        else :
            self.log.write(f"{Fore.RED}{Style.BRIGHT}not found{Style.RESET_ALL}"
                           f" {patt}{Fore.WHITE}{Style.DIM}@{Style.RESET_ALL}"
                           f"{path}\n")
        self.out.write(f"{int(found)}\n")
        return found

##
## CLI
##

parser = argparse.ArgumentParser("badass",
                                 description="(not so) bad assessments")
parser.add_argument("-o", "--out", default=sys.stdout,
                    type=argparse.FileType("w", encoding="utf-8"),
                    metavar="PATH",
                    help="print results to PATH")
parser.add_argument("-l", "--log", default=sys.stderr,
                    type=argparse.FileType("w", encoding="utf-8"),
                    metavar="PATH",
                    help="print log messages to PATH")
parser.add_argument("-d", "--db", default="bad.db", metavar="PATH",
                    help="PATH to database for result records (default 'bad.db')")
parser.add_argument("-r", "--record", default=None, type=str, metavar="PROJECT:TEST",
                    help="record result has TEST in PROJECT (two names)")
parser.add_argument("base", metavar="DIR",
                    help="path of project base directory")
sub = parser.add_subparsers(dest="command",
                            required=True,
                            title="available commands")

patch = sub.add_parser("patch",
                       help="patch a file")
patch.add_argument("path",
                   help="file to be patched")
patch.add_argument("expr",
                   nargs="+",
                   help="patch directives (del NAME / add PATH@NAME)")

xpath = sub.add_parser("xpath",
                       help="query a file using xpath")
fmt = xpath.add_mutually_exclusive_group()
fmt.add_argument("-s", "--source", action="store_true", default=False,
                 help="output result as source code (default)")
fmt.add_argument("-x", "--xml", action="store_true", default=False,
                 help="output result as XML")
fmt.add_argument("-c", "--count", action="store_true", default=False,
                 help="output result as the number of matches")
xpath.add_argument("path",
                   help="file to be searched in")
xpath.add_argument("expr",
                   help="xpath expression")

has = sub.add_parser("has",
                     help="check for a declaration")
has.add_argument("decl",
                 help="declaration to be searched for (name or signature)")

args = parser.parse_args()
badcli = BadassCLI(args.base, args.out, args.log)
badcli(args)
