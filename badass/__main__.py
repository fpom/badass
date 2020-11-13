import argparse, pathlib, importlib, sys, functools, ast, time
import subprocess, signal
import psutil
import lxml.etree
import tqdm
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

def _const (val) :
    if isinstance(val, str) :
        val = ast.literal_eval(val)
    if isinstance(val, bool) :
        return int(val)
    else :
        return val

def killtree (pid) :
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for p in children:
        p.send_signal(signal.SIGTERM)
    _, alive = psutil.wait_procs(children)
    if alive :
        time.sleep(0.2)
        for p in alive :
            p.send_signal(signal.SIGKILL)

class BadassCLI (object) :
    def __init__ (self, path, out, log, lang) :
        self.path = pathlib.Path(path)
        self.out = out
        self.log = log
        self.lang = lang.lower()
        self.mod = importlib.import_module("." + self.lang, "badass")
        self.src = {}
    def __call__ (self, args) :
        cmd = getattr(self, "do_" + args.command)
        cmd(args)
    def _source_load (self, path, source=None) :
        if not pathlib.Path(path).name.startswith(".") :
            self.log.write(f"{Fore.BLUE}{Style.BRIGHT}load{Style.RESET_ALL} {path}\n")
        path = (self.path / pathlib.Path(".//" + str(path))).relative_to(self.path)
        if path in self.src :
            return self.src[path]
        src = self.src[path] = self.mod.source.Source(str(self.path / path), source)
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
        self._csrc = getattr(self, "_csrc", 0) + 1
        decl = self._source_load(f".{self._csrc}.c", patt + ";")
        name = next(iter(decl.d))
        try :
            code = self._source_load(path)
            if decl.sig(name) == name :
                found = name in code.d
            else :
                found = name in code.d and decl.sig(name) == code.sig(name)
        except FileNotFoundError :
            found = False
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
    ## cparse
    ##
    def do_cparse (self, args) :
        if args.input :
            code = args.input.read()
        else :
            code = args.code
        self._csrc = getattr(self, "_csrc", 0) + 1
        src = self._source_load(f".{self._csrc}.c", code)
        xml = lxml.etree.tostring(src.x, pretty_print=True, encoding="utf-8")
        self.out.write(xml.decode("utf-8"))
        self.out.write("\n")
    ##
    ## run
    ##
    _runcolor = {"out" : Fore.GREEN,
                 "err" : Fore.RED,
                 "sys" : Fore.MAGENTA,
                 "ret" : Fore.BLUE,
                 "*"   : Fore.YELLOW}
    def _badass_h (self, path) :
        import pkg_resources
        _path = pathlib.Path(path)
        if _path.name == "badass.h" and not _path.exists() :
            return pkg_resources.resource_filename("badass.c", "badass.h")
        else :
            return path
    @record
    def do_run (self, args) :
        self.log.write(f"{Fore.BLUE}{Style.BRIGHT}run{Style.RESET_ALL} {args.base}\n")
        add, rep = set(), set()
        for a in args.add :
            add.update(self._badass_h(p) for p in a)
        for a in args.replace :
            rep.update(self._badass_h(p) for p in a)
        runner = self.mod.run.AssRunner(add, rep)
        run = runner(args.base, timeout=args.timeout)
        for key, val in run.items() :
            if not getattr(args, key.rsplit(".", 1)[-1], None) :
                continue
            elif val is None or (isinstance(val, str) and not val) :
                continue
            color = self._runcolor.get(key.split(".", 1)[-1], self._runcolor["*"])
            self.out.write(f"{color}=== {key} ==={Style.RESET_ALL}\n")
            if isinstance(val, str) :
                self.out.write(val)
            elif getattr(val, "_print", None) :
                getattr(val, "_print")(self.out)
            else :
                self.out.write(repr(val))
            self.out.write("\n")
        return run
    ##
    ## report
    ##
    def do_report (self, args) :
        import pandas as pd
        self.log.write(f"{Fore.BLUE}{Style.BRIGHT}save{Style.RESET_ALL} {args.outfile}\n")
        db = DB(args.db)
        data = {}
        for row in db.checks() :
            data.setdefault(row.project, {})
            data[row.project][row.test] = _const(row.result)
        for row in db.runs() :
            data.setdefault(row.project, {})
            ass = ast.literal_eval(open(row.run_ass).read())
            for key, (result, _) in ass.items() :
                data[row.project][f"{row.test}_{key}"] = _const(result == "passed")
            data[row.project][f"{row.test}_build"] = _const(row.build_ret == "0")
        df = pd.DataFrame.from_dict(data, orient="index")
        df.to_csv(args.outfile, index=True, index_label="project")
    ##
    ## p5
    ##
    def do_p5 (self, args) :
        from .p5 import PrePreProcessor
        g = dict(a.split("=", 1) for a in args.let)
        p = PrePreProcessor(*args.input,
                            comment=args.marker,
                            include=args.include,
                            **g)
        if args.save :
            p.save(args.save)
        if args.nocpp :
            args.output.write(p.ppp)
        else :
            args.output.write(p.cpp)
    ##
    ## compare
    ##
    def do_compare (self, args) :
        from .dist import Dist
        if args.load :
            dist = Dist.read_csv(args.load)
        else :
            projects = list(args.project)
            dist = Dist([pathlib.Path(p).name for p in projects])
            todo = [(p, q) for i, p in enumerate(projects) for q in projects[i+1:]]
            for p, q in tqdm.tqdm(todo) :
                kp = pathlib.Path(p).name
                kq = pathlib.Path(q).name
                dist.add(kp, p, kq, q, *args.glob)
        if args.csv :
            dist.csv(args.csv)
        if args.heatmap :
            options = {}
            for opt in args.hmopt :
                key, val = opt.split("=", 1)
                try :
                    val = ast.literal_eval(val)
                except :
                    pass
                options[key] = val
            dist.heatmap(args.heatmap, max_size=args.maxsize, absolute=args.absolute,
                         **options)
    def do_trace (self, args) :
        strace = subprocess.Popen(["strace", "-f", "-r", "-o", "run.sys"] + args.cmd,
                                  encoding="utf-8",
                                  stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        start = time.time()
        while True :
            time.sleep(0.1)
            if strace.poll() is not None :
                break
            elif time.time() - start > args.timeout :
                killtree(strace.pid)
        with open("run.ret", "w") as out :
            out.write(f"{strace.returncode}\n")
        with open("run.out", "w") as out :
            out.write(strace.stdout.read())
        with open("run.err", "w") as out :
            out.write(strace.stderr.read())
        with open("run.dm", "w") as out :
            for path in sorted(pathlib.Path(".").glob("run.dm.*"),
                               key=lambda p: int(p.name.rsplit(".")[-1])) :
                pid = path.name.rsplit(".")[-1]
                for line in open(path) :
                    out.write(f"{pid}:" + line.split(":", 2)[-1])

##
## CLI
##

parser = argparse.ArgumentParser("badass",
                                 description="(not so) bad assessments")
parser.add_argument("-o", "--output", default=sys.stdout,
                    type=argparse.FileType("w", encoding="utf-8"),
                    metavar="PATH",
                    help="print results to PATH (default: stdout)")
parser.add_argument("-l", "--log", default=sys.stderr,
                    type=argparse.FileType("w", encoding="utf-8"),
                    metavar="PATH",
                    help="print log messages to PATH (default: stderr)")
parser.add_argument("--lang", type=str, default="C",
                    help="programming language for the project (default: 'C')")
parser.add_argument("--db", default="bad.db", metavar="PATH",
                    help="PATH to database for result records (default 'bad.db')")
parser.add_argument("--record", default=None, type=str, metavar="PROJECT:TEST",
                    help="record result as TEST in PROJECT (two arbitrary tags)")
parser.add_argument("-b", "--base", metavar="DIR", default=".",
                    help="path of project base directory (default: '.')")
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

cparse = sub.add_parser("cparse",
                        help="parse C code and dump it as XML")
cparse.add_argument("-i", "--input", metavar="PATH",
                    type=argparse.FileType("r", encoding="utf-8"),
                    help="read code from PATH")
cparse.add_argument("code", help="C code", default="", nargs="?")

run = sub.add_parser("run",
                     help="build and execute a project")
run.add_argument("-t", "--timeout", default=60, type=int,
                 help="limit of CPU runtime, in seconds (default 60)")
run.add_argument("--out", default=False, action="store_true",
                 help="show stdout")
run.add_argument("--err", default=False, action="store_true",
                 help="show stderr")
run.add_argument("--ret", default=False, action="store_true",
                 help="show return codes")
run.add_argument("--sys", default=False, action="store_true",
                 help="show strace")
run.add_argument("-a", "--add", metavar="FILE",
                 nargs="+", action="append", default=[],
                 help="files to add to the project (unless already present)")
run.add_argument("-r", "--replace", metavar="FILE",
                 nargs="+", action="append", default=[],
                 help="files to replace in the project (or add if absent)")

report = sub.add_parser("report",
                        help="dump database to CSV")
report.add_argument("outfile", default="badass.csv", type=str, nargs="?",
                    help="file name to be saved (default 'badass.csv')")

ppppp = sub.add_parser("p5",
                       help="Python-powered pre-pre-processor")
ppppp.add_argument("-I", metavar="DIR", action="append", default=[], dest="include",
                   help="add DIR the the set of paths searched for includes")
ppppp.add_argument("-m", "--marker", default="//", type=str,
                   help="directives marker (default: '//')")
ppppp.add_argument("-l", "--let", metavar="NAME=EXPR", default=[], action="append",
                   type=str, help="define additional names, as with let directive")
ppppp.add_argument("-s", "--save", metavar="FILE", default=None,
                   type=argparse.FileType("w", encoding="utf-8"),
                   help="save ppppped text to FILE")
ppppp.add_argument("-n", "--nocpp", default=False, action="store_true",
                   help="output text whithout passing it to cpp")
ppppp.add_argument("input", metavar="FILE", nargs="+",
                   type=argparse.FileType("r", encoding="utf-8"),
                   help="input FILEs to process")

compare = sub.add_parser("compare",
                         help="compare projects")
compare.add_argument("-g", "--glob", metavar="GLOB", default=[], action="append",
                     help="files to include in comparison")
compare.add_argument("--csv", type=argparse.FileType("w", encoding="utf-8"),
                     help="save distance matrix to CSV")
compare.add_argument("--heatmap", metavar="PATH", type=str, default=None,
                     help="draw a clustered heatmap in PATH")
compare.add_argument("--hmopt", default=[], action="append", type=str,
                     help="additional options for heatmap")
compare.add_argument("--maxsize", metavar="COUNT", type=int, default=0,
                     help="split heatmap into clusters of at most COUNT projects")
compare.add_argument("--absolute", default=False, action="store_true",
                     help="draw heatmap with absolute colors")
compare.add_argument("--load", default=None, action="store", type=str, metavar="CSV",
                     help="load distance matrix from CSV instead of computing it")
compare.add_argument("project", default=[], type=str, nargs="*",
                     help="project base dir (or single file)")

trace = sub.add_parser("trace",
                       help="run a process and trace it")
trace.add_argument("-t", "--timeout", default=60, type=int,
                   help="kill the process after given TIMEOUT")
trace.add_argument("cmd",
                   nargs="+",
                   help="command to be run and traced")

def main () :
    args = parser.parse_args()
    badcli = BadassCLI(args.base, args.output, args.log, args.lang)
    badcli(args)

if __name__ == "__main__" :
    main()
