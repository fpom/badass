import subprocess, json, io, collections, pathlib

from pathlib import Path

from ...run.queries import query
from ... import encoding, tree, recode
from .cnip import cnip
from .. import BaseASTPrinter

def _cc1 (src) :
    cc = subprocess.run(["clang", "-cc1", "-ast-dump=json"],
                        input=src, capture_output=True,
                        **encoding)
    if cc.returncode == 0 :
        return json.loads(cc.stdout)
    else :
        raise SystemError(f"clang exited with code {cc.returncode}: {cc.stderr}")

def tidy (sig, decl=None) :
    ignore = set()
    sig = sig.rstrip().rstrip(";") + ";"
    if decl :
        decl = decl.rstrip().rstrip(";") + ";"
        for obj in _cc1(decl)["inner"] :
            ignore.add(obj.get("name"))
        ast = _cc1(decl + sig)
    else :
        ast = _cc1(sig)
    for obj in ast["inner"] :
        if obj.get("isImplicit") :
            continue
        name = obj.get("name")
        if name in ignore :
            continue
        if name :
            return obj["type"]["qualType"].replace("(", f"{name}(", 1)
        else :
            return obj["type"]["qualType"]

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
                files.extend(path.glob("*.[ch]"))
            else :
                # check if it's relative to identified base directory
                path.relative_to(self.base_dir)
                files.append(path)
        self.ast = {}
        self.obj = {}
        self.sig = collections.defaultdict(list)
        self.src = {}
        for path in files :
            recode(path)
            self.parse(path)
    def parse (self, path) :
        _path = str(path.relative_to(self.base_dir))
        source = io.StringIO()
        with open(path, **encoding) as src :
            for line in src :
                if line.startswith("#include") :
                    source.write("//")
                source.write(line)
        done = subprocess.run(["clang", "-cc1", "-ast-dump=json", _path],
                              cwd=self.base_dir,
                              input=source.getvalue(),
                              capture_output=True,
                              **encoding)
        ast = tree(json.loads(done.stdout))
        self.ast[_path] = {"clang" : ast,
                           "cnip" : cnip.parse(path).dict()}
        for decl in query("$..*[?kind='FunctionDecl']", ast) :
            if decl.get("isImplicit", False) :
                continue
            n = decl["name"]
            t = decl["type"]["qualType"]
            tn = t.replace("(", f"{n}(", 1)
            self.obj[n] = self.obj[tn] = (_path, tree(decl))
            self.sig[t].append((_path, n))
            self.sig[n].extend([(_path, tn), (_path, t)])
        for decl in query("$..*[?kind='TypedefDecl']", ast) :
            if decl.get("isImplicit", False) :
                continue
            n = decl["name"]
            t = decl["type"]["qualType"]
            self.obj[n] = self.obj[t] = (_path, tree(decl))
            self.sig[t].append((_path, n))
    def __getitem__ (self, loc) :
        path, line = loc
        if path not in self.src :
            _path = self.base_dir / path
            self.src[path] = tuple(l.rstrip(b"\n\r") for l in _path.open("rb"))
        return self.src[path][line]
    def __iter__ (self) :
        for path in self.ast :
            yield pathlib.Path(path)
    def decl (self, signature, declarations=None) :
        info = self.obj.get(tidy(signature, declarations), None)
        if info is not None :
            return info[1]
    def source (self, name) :
        try :
            path, ast = self.obj[name]
        except KeyError :
            return None
        path = self.base_dir / path
        begin = ast.range.begin.offset
        end = ast.range.end.offset + ast.range.end.tokLen
        src = path.read_bytes()
        return src[begin:end].decode("utf-8", errors="replace")
    def discard (self, name) :
        path, ast = self.obj[name]
        self.sig.pop(name, None)
        path = self.base_dir / path
        begin = ast.range.begin.offset
        end = ast.range.end.offset + 1
        src = path.read_bytes()
        with path.open("wb") as out :
            out.write(src[:begin])
            lno = len(src[:end].splitlines())
            out.write(b"#line %i\n" % lno)
            out.write(src[end:])
        self.parse(path)
    def add (self, source, path) :
        with path.open("w", **encoding) as out :
            for line in source.splitlines(keepends=True) :
                if line.startswith("//signature ") :
                    name = line.split(None, 1)[-1].strip()
                    try :
                        out.write(self.sig[name][0][1] + ";\n")
                    except :
                        out.write(f"//missing signature for {name}\n")
                else :
                    out.write(line)
        self.parse(path)

class ASTPrinter (BaseASTPrinter) :
    IMPORTANT = {"clang" : ["kind", "id"],
                 "cnip" : ["kind"]}
    GROUP = {"clang" : {},
             "cnip" : {("start_line", "end_line") : "line: {start_line}:{end_line}",
                       ("start_char", "end_char") : "char: {start_char}:{end_char}"}}
    CHILDREN = {"clang" : ["inner"],
                "cnip" : ["children"]}
    FORMAT = {"clang" : {"qualType" : "{val!r}"},
              "cnip" : {"snippet" : "{val!r}"}}
    IGNORE = {"clang" : [],
              "cnip" : ["src"]}
