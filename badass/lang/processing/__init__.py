import json, collections

from subprocess import run as subprocess_run, PIPE, STDOUT
from pathlib import Path

from .. import BaseLanguage, BaseASTPrinter
from ... import tree, encoding, cached_property, mdesc, recode
from .parser import SourceTree, tidy

class Source (object) :
    def __init__ (self, *paths) :
        self.base_dir = None
        files = []
        for path in (Path(p) for p in paths) :
            if self.base_dir is None :
                if path.is_dir() :
                    self.base_dir = path
                else :
                    self.base_dir = path.parent
            if path.is_dir() :
                # check if it's relative to identified base directory
                path.relative_to(self.base_dir)
                files.extend(path.glob("*.pde"))
            else :
                # check if it's relative to identified base directory
                path.relative_to(self.base_dir)
                files.append(path)
        self.ast = {}
        self.tree = {}
        self.obj = {}
        for path in files :
            recode(path)
            self.parse(path)
    def parse (self, path) :
        _path = str(path.relative_to(self.base_dir))
        tree = self.tree[_path] = SourceTree.parse(path)
        self.ast[_path] = {"treesitter" : {"kind" : f"{tree.kind}_program",
                                           "children" : list(tree.dump_all())}}
    def _add_obj (self, tree) :
        for method in tree("(method_declaration) @method")["method"] :
            q = """(method_declaration
                     type: (_) @type
                     name: (_) @name
                     parameters: (_
                                   (formal_parameter)* @params
            ))"""
            match = tree(q, method)
            if match :
                nam = tree[match["name"][0]]
                typ = tree[match["type"][0]]
                par = ", ".join(tree[n] for n in match.get("params", []))
                sig = tidy(f"{typ} {nam}({par})")
                self.obj[nam] = self.obj[sig] = (tree, method)
    def decl (self, sig, decl=None) :
        if decl is not None :
            raise ValueError("parameter 'decl' not supported by language")
        sig = sig.strip()
        if sig not in self.obj :
            sig = tidy(sig)
        if sig in self.obj :
            tree, node = self.obj[sig]
            return tree.dump(node)
        else :
            return None
    def add (self, source, path) :
        with path.open("w", **encoding) as out :
            out.write(source)
        self.parse(path)
    def discard (self, name) :
        old, node = self.obj[name]
        _path = str(old.path.relative_to(self.base_dir))
        new = old.discard(node)
        if new :
            self.ast[_path] = {"treesitter" : {"kind" : f"{new.kind}_program",
                                               "children" : list(new.dump_all())}}
            for key in [k for k, (_, n) in self.obj.items() if n is node] :
                del self.obj[key]
        else :
            del self.ast[_path]
            for key in [k for k, (s, _) in self.obj.items() if s is old] :
                del self.obj[key]

class ASTPrinter (BaseASTPrinter) :
    IMPORTANT = {"treesitter" : ["kind"]}
    GROUP = {}
    CHILDREN = {"treesitter" : ["children"]}
    FORMAT = {}
    IGNORE = {}

class Language (BaseLanguage) :
    SUFFIX = ".pde"
    NAMES = ["Processing"]
    DESCRIPTION = "Processing language (Java mode)"
    #FIXME when AST is available
    MACROS = {"LoopStmt" : ("ForStmt", "WhileStmt"),
              "CondStmt" : ("IfStmt", "SwitchStmt")}
    IGNORE = {}
    def __init__ (self, test) :
        super().__init__(test)
        self.log = []
        self.dir = self.test.test_dir
        for path, _ in self.test.repo :
            if path.suffix == self.SUFFIX :
                self.sketch = path.stem
                self.test.repo.copytree("src", self.sketch)
                break
        else :
            self.sketch = "src"
    @cached_property
    def source (self) :
        return Source(self.test.test_dir / self.sketch)
    def add_source (self, source, path) :
        self.source.add(source, path)
    def del_source (self, name) :
        self.source.discard(name)
    def decl (self, sig, decl=None) :
        return self.source.decl(sig, decl)
    def make_script (self) :
        # start program within X11
        xstart_path = self.test.repo.new("xstart.sh")
        with xstart_path.open("w", **encoding) as xstart :
            env = "log/run/xstart.env"
            ret = "log/run/run.status"
            xstart.write(f"echo $$ > log/run/xstart.pid\n"
                         f"echo DISPLAY=$DISPLAY > {env} \n"
                         f"echo XAUTHORITY=$XAUTHORITY >> {env}\n"
                         f"jwm >/dev/null 2>&1 &\n"
                         f"echo WM=$! >> {env}\n"
                         f"{self.sketch}.out/{self.sketch}\n"
                         f"echo $? > {ret}\n")
        # stop X11 program
        xstop_path = self.dir / "xstop.sh"
        with xstop_path.open("w", **encoding) as xstop :
            xstop.write(f". log/run/xstart.env\n"
                        f"export DISPLAY XAUTHORITY\n"
                        f"wmctrl -l\n"
                        f"echo '######'\n"
                        f"for WINID in $(wmctrl -l|awk '{{print $1}}')\n"
                        f"do\n"
                        f"  echo closing $WINID\n"
                        f"  wmctrl -i -c $WINID\n"
                        f"done\n"
                        f"kill $WM\n"
                        f"exit 0\n")
        # main script
        make_path = self.dir / "make.sh"
        with make_path.open("w", **encoding) as script :
            for sub in ("build", "run") :
                script.write(f"mkdir -p log/{sub}\n")
            script.write(f"echo $$ > log/build/make.pid\n"
                         f"env > log/build/make.env\n"
                         f"echo '######' >> log/build/make.env\n"
                         f"echo PROCESSING=$(which processing-java) >> log/build/make.env\n"
                         f"echo PROCESSING_VERSION=$(processing-java --help|grep .|head -n 1) >> log/build/make.env\n")
            # build program
            comp = (f"processing-java"
                    f" --sketch={self.sketch}"
                    f" --output={self.sketch}.out"
                    f" --export")
            out = "log/build/build.stdout"
            ret = "log/build/build.status"
            script.write(f"rm -f {self.sketch}.out\n"
                         f"{comp} > {out} 2>&1\n"
                         f"echo $? > {ret}\n")
            self.log.append(["compile", self.sketch, comp,
                             tree(stdout=out, exit_code=ret)])
            # run program
            err = "log/run/run.stderr"
            script.write(f"xvfb-run -a -l /bin/bash {xstart_path.name} 2> {err}\n"
                         f"echo\n"
                         f"exit 0")
        return make_path, xstop_path
    @property
    def exit_code (self) :
        ret = (self.dir / "log/run/run.status").read_text(**encoding).strip()
        try :
            return int(ret)
        except :
            return ret
    def checks (self) :
        self.test.repo.update(f"{self.sketch}", f"{self.sketch}.out/source")
        yield "compile", "build", list(self.report_build())
    def report_build (self) :
        for action, path, cmd, stdio in self.log :
            success = (self.dir / stdio.exit_code).read_text(**encoding).strip() == "0"
            stdout = (self.dir / stdio.stdout).read_text(**encoding)
            if stdout.strip() :
                details = f"`$ {cmd}`\n<pre>\n{mdesc(stdout)}\n<pre>"
            else :
                details = f"`$ {cmd}`"
            yield success, f"{action} `{path}`", details, None
