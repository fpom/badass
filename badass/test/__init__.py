import ast, collections, shutil, shlex

from collections import namedtuple
from zipfile import ZipFile
from pathlib import Path
from csv import DictReader
from io import TextIOWrapper
from subprocess import check_call
from colorama import Style as S, Fore as F

##
## parse badass.csv
##

field = namedtuple("field", ("name", "type", "default", "label"))

def optparse (text) :
    mod = ast.parse(text)
    for ass in mod.body :
        yield ass.targets[0].id, str(ass.value.value)

class BadParser (object) :
    def __call__ (self, path) :
        reader = DictReader(open(path))
        fields = {f for f in reader.fieldnames if f != "options"}
        for row in reader :
            for key, val in optparse(row.pop("options", "")) :
                if parse := getattr(self, f"_parse_{key}", None) :
                    val = parse(val)
                if key in fields :
                    row[key] = val
                elif key not in row :
                    row[key] = val
                elif isinstance(row[key], list) :
                    row[key].append(val)
                else :
                    row[key] = [row[key], val]
            for key, val in row.items() :
                if fmt := getattr(self, f"_format_{key}", None) :
                    row[key] = fmt(val)
            yield row
    def _parse_subtitle (self, text) :
        return text.replace("##", "#")
    def _parse_input (self, text) :
        return field(*text.split(":", 3))
    def _as_list (self, value) :
        if isinstance(value, list) :
            return value
        else :
            return [value]
    def _format_source (self, value) :
        return self._as_list(value)
    def _format_input (self, value) :
        return self._as_list(value)


badparse = BadParser()

##
## execute 'badass run'
##

def log (msg) :
    print(f"{F.BLUE}[test]{F.RESET} {msg.strip()}")

def badass_run (script, sources, testdir, inputs, debug) :
    target = Path(testdir)
    if target.exists() :
        log(f"rm -rf {target}")
        shutil.rmtree(target)
    target_src = target / "src"
    target_src.mkdir(parents=True)
    for src in sources :
        log(f"cp {src} {target_src}/")
        shutil.copy(src, target_src)
    argv = ["badass", "run"]
    if debug :
        argv.append("--debug")
    for inp in inputs :
        argv.extend(["-d", f"{inp.name}={inp.default}"])
    argv.extend([str(script), str(target)])
    log(shlex.join(argv))
    check_call(argv)

##
## read and display report
##

class tree (object) :
    def __init__ (self, *labels, test="", status=None, auto=False, text="", details="") :
        if status :
            stat = {"pass": f"{F.GREEN}[PASS]",
                    "warn": f"{F.YELLOW}[WARN]",
                    "fail": f"{F.RED}[FAIL]"}.get(status, "")
            label = f"{stat}{S.RESET_ALL} {text}"
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

def report (path) :
    with open(path, "rb") as zdata, ZipFile(zdata) as zf :
        infile = TextIOWrapper(zf.open("report.csv"), encoding="utf-8", errors="replace")
        report = list(DictReader(infile))
    root = tree(Path(path).parent.stem)
    nodes = {"" : root}
    for test in report :
        num = f".{test['test']}"
        pid, cid = num.rsplit(".", 1)
        nodes[num] = tree(**test)
        nodes[pid].children.append(nodes[num])
    root.print()
