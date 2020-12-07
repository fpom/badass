import subprocess, json, io, re, collections, pathlib

from itertools import count

from ...run.queries import query
from ... import encoding, tree, recode

_tidy_multi = re.compile(r"\b\s{2,}\b")
_tidy_words = re.compile(r"(\B\s+\b)|(\b\s+\B)|(\B\s+\B)")

def tidy (decl) :
    return _tidy_words.sub(" ", _tidy_multi.sub(" ", decl.strip()))

class Source (object) :
    def __init__ (self, base_dir, source_files) :
        self.base_dir = base_dir
        self.ast = {}
        self.obj = {}
        self.sig = collections.defaultdict(list)
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
            t = tidy(decl["type"]["qualType"])
            tn = tidy(t.replace("(", f"{n}(", 1))
            self.obj[n] = self.obj[tn] = (_path, tree(decl))
            self.sig[t].append((_path, n))
            self.sig[n].extend([(_path, tn), (_path, t)])
        for decl in query("$..*[?kind='TypedefDecl']", ast) :
            if decl.get("isImplicit", False) :
                continue
            n = decl["name"]
            t = tidy(decl["type"]["qualType"])
            self.obj[n] = self.obj[t] = (_path, tree(decl))
            self.sig[t].append((_path, n))
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
        end = ast.range.end.offset
        src = path.read_text(**encoding)
        with path.open("w", **encoding) as out :
            out.write(src[:begin])
            out.write("/*")
            out.write(src[begin:end])
            out.write("*/")
            out.write(src[end:])
        self.parse(path)
    def add (self, source, path) :
        with path.open("w", **encoding) as out :
            for line in source.splitlines(keepends=True) :
                if line.startswith("//signature ") :
                    name = line.split(None, 1)[-1].strip()
                    out.write(self.sig[name][0][1] + ";\n")
                else :
                    out.write(line)
        self.parse(path)
