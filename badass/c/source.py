import subprocess
from lxml import etree
import chardet

from clang.cindex import Index, Config, CursorKind
if not getattr(Config, "library_file", None) :
    Config.set_library_file("/usr/lib/llvm-9/lib/libclang.so")

_cpp_head = ""

def cpp (src, env={}, **var) :
    _env = dict(env)
    _env.update(var)
    src = subprocess.run(["cpp", "-P", "--traditional", "-C"]
                         + [f"-D{k}={v}" for k, v in _env.items()],
                         input=src, encoding="utf-8", capture_output=True).stdout
    return src.replace(_cpp_head, "")

_cpp_head = cpp("")

class Source (object) :
    def __init__ (self, path, source=None) :
        self.p = path
        self.i = Index.create()
        if source is None :
            data = open(path, "rb").read()
            enc = chardet.detect(data)
            self.s = data.decode(enc["encoding"]).splitlines()
            self.t = self.i.parse(path)
        else :
            self.s = source.splitlines()
            self.t = self.i.parse(path, unsaved_files=[(path, source)])
        self.d = {}
        for child in self.t.cursor.get_children() :
            if (child.location.file.name == path
                and (child.is_definition()
                     or child.kind in (CursorKind.ENUM_CONSTANT_DECL,
                                       CursorKind.ENUM_DECL,
                                       CursorKind.FUNCTION_DECL,
                                       CursorKind.STRUCT_DECL,
                                       CursorKind.TYPEDEF_DECL,
                                       CursorKind.TYPE_ALIAS_DECL,
                                       CursorKind.UNION_DECL,
                                       CursorKind.VAR_DECL))) :
                self.d[child.spelling] = child
        self.x = self.xml()
    def __iter__ (self) :
        return iter(self.d)
    def src (self) :
        return "\n".join(self.s) + "\n"
    def add (self, src) :
        self.s.extend(src.splitlines())
    def node (self, name) :
        return self.d[name]
    def sig (self, name) :
        decl = self.d[name]
        if decl.result_type.spelling :
            return f"{decl.result_type.spelling} {decl.displayname}"
        else :
            return f"{decl.displayname}"
    def loc (self, name) :
        decl = self.d[name]
        return self.p, decl.extent.start.line, decl.extent.end.line
    def _get_slice (self, sl, sc, el, ec) :
        lines = self.s[sl-1:el]
        lines[0] = lines[0][sc-1:]
        lines[-1] = lines[-1][:ec-1]
        return "\n".join(lines)
    def __getitem__ (self, name) :
        decl = self.d[name]
        return self._get_slice(decl.extent.start.line,
                               decl.extent.start.column,
                               decl.extent.end.line,
                               decl.extent.end.column)
    def __delitem__ (self, name) :
        decl = self.d[name]
        pos = decl.extent.start.line - 1
        self.s[pos] = self.s[pos][:decl.extent.start.column - 1]
        pos = decl.extent.end.line - 1
        self.s[pos] = self.s[pos][decl.extent.end.column - 1:]
        for pos in range(decl.extent.start.line, decl.extent.end.line - 1) :
            self.s[pos] = ""
    def __call__ (self, expr, fmt="src") :
        val = self.x.xpath(expr)
        if isinstance(val, list) :
            return [self._xpath(v, fmt) for v in val]
        else :
            return self._xpath(val, fmt)
    def _xpath (self, val, fmt) :
        if isinstance(val, (int, str)) or val is None :
            return val
        elif fmt == "src" :
            return self._get_slice(int(val.attrib["startline"]),
                                   int(val.attrib["startcol"]),
                                   int(val.attrib["endline"]),
                                   int(val.attrib["endcol"]))
        elif fmt == "xml" :
            return val
        elif fmt == "node" :
            return self._x[val]
    def xml (self) :
        self._x = {}
        root = etree.Element("CTU",
                             file=self.p,
                             startline=str(self.t.cursor.extent.start.line),
                             startcol=str(self.t.cursor.extent.start.column),
                             endline=str(self.t.cursor.extent.end.line),
                             endcol=str(self.t.cursor.extent.end.column))
        for child in self.t.cursor.get_children() :
            if child.location.file.name == self.p :
                self._xml(child, root)
        return root
    def _xml (self, node, xparent) :
        xchild = etree.SubElement(xparent, node.kind.name.lower(),
                                  startline=str(node.extent.start.line),
                                  startcol=str(node.extent.start.column),
                                  endline=str(node.extent.end.line),
                                  endcol=str(node.extent.end.column))
        self._x[xchild] = node
        for name in dir(node) :
            try :
                obj = getattr(node, name)
            except :
                continue
            if name.startswith("is_") and callable(obj) :
                xchild.attrib[name] = str(obj()).lower()
            elif not obj :
                pass
            elif not name.startswith("_") :
                txt = str(obj).lower()
                if txt.startswith("<") :
                    continue
                xchild.attrib[name] = str(obj).lower()
        for child in node.get_children() :
            self._xml(child, xchild)
