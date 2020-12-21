import subprocess, json, io, collections, pathlib

from ...run.queries import query
from ... import encoding, tree, recode

def tidy (decl) :
    dump = subprocess.check_output(["clang", "-cc1", "-ast-dump=json"],
                                   input=decl.rstrip(";") + ";",
                                   stderr=subprocess.DEVNULL,
                                   **encoding)
    ast = json.loads(dump)
    for obj in ast["inner"] :
        if not obj.get("isImplicit", False) :
            name = obj.get("name")
            if name :
                return obj["type"]["qualType"].replace("(", f"{name}(", 1)
            else :
                return obj["type"]["qualType"]

class Source (object) :
    def __init__ (self, base_dir, source_files) :
        self.base_dir = base_dir
        self.ast = {}
        self.obj = {}
        self.sig = collections.defaultdict(list)
        self.src = {}
        for path in source_files :
            if path.match("*.[ch]") :
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
        ast = self.ast[_path] = tree(json.loads(done.stdout))
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
    def decl (self, signature) :
        info = self.obj.get(tidy(signature), None)
        if info is not None :
            return info[1]
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
