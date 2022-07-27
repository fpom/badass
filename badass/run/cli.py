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
    sub.add_argument("--debug", action="store_true", default=False,
                     help="print ignored exceptions")
    sub.add_argument("-s", "--summary", action="store_true", default=False,
                     help="summarise report on stdout")
    sub.add_argument("script", type=str,
                     help="path to script")
    sub.add_argument("project", type=str,
                     help="path to project")

def summary (path) :
    from zipfile import ZipFile
    from pathlib import Path
    from csv import DictReader
    from sys import argv
    from io import TextIOWrapper
    from colorama import Style, Fore
    class tree (object) :
        def __init__ (self, *labels, test="", status=None, auto=False,
                      text="", details="") :
            if status :
                stat = {"pass": f"{Fore.GREEN}[PASS]",
                        "warn": f"{Fore.YELLOW}[WARN]",
                        "fail": f"{Fore.RED}[FAIL]"}.get(status, "")
                label = f"{stat}{Style.RESET_ALL} {text}"
            else :
                label = " ".join(labels)
            self.label = label
            self.children = []
            for child in self.children :
                if isinstance(child, tree) :
                    self.children.append(child)
                else :
                    self.children.append(tree(child))
        def print (self, prefix=None, last=True) :
            if prefix is None :
                print(self.label)
            elif last :
                print(prefix + " └─", self.label)
            else :
                print(prefix + " ├─", self.label)
            for child in self.children :
                if prefix is None :
                    child.print("", child is self.children[-1])
                elif last :
                    child.print(prefix + "    ", child is self.children[-1])
                else :
                    child.print(prefix + " │  ", child is self.children[-1])
    with (Path(path) / "report.zip").open("rb") as zdata, \
         ZipFile(zdata) as zf :
        infile = TextIOWrapper(zf.open("report.csv"), encoding="utf-8", errors="replace")
        report = list(DictReader(infile))
    root = tree(Path(argv[-1]).stem)
    nodes = {"" : root}
    for test in report :
        num = f".{test['test']}"
        pid, cid = num.rsplit(".", 1)
        nodes[num] = tree(**test)
        nodes[pid].children.append(nodes[num])
    root.print()

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
    if args.summary :
        summary(args.project)
