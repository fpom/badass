from lxml import etree

from clang.cindex import Index, Config
if not getattr(Config, "library_file", None) :
    Config.set_library_file("/usr/lib/llvm-9/lib/libclang.so")

class C (object) :
    def __init__ (self, path) :
        self.p = path
        self.s = open(path).read().splitlines()
        self.i = Index.create()
        self.t = self.i.parse(path)
        self.d = {}
        for child in self.t.cursor.get_children() :
            if child.location.file.name == path and child.is_definition() :
                self.d[child.spelling] = child
        self.x = self.xml()
    def __iter__ (self) :
        return iter(self.d)
    def __repr__ (self) :
        return "\n".join(self.s)
    def node (self, name) :
        return self.d[name]
    def sig (self, name) :
        decl = self.d[name]
        return f"{decl.result_type.spelling} {decl.displayname}"
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
        root = etree.Element("CTU", file=self.p)
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
