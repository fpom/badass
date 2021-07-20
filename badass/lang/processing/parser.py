import sys, ast, collections

from pathlib import Path

from tree_sitter import Language, Parser

from ... import encoding

import badass.lang

JAVA = Language(Path(badass.lang.__file__).parent / "tslib.so", "java")
parser = Parser()
parser.set_language(JAVA)

def _query_captures (query, root) :
    # this fixes duplicated captured nodes when * is used in queries
    seen = set()
    for node, name in JAVA.query(query).captures(root) :
        nsig = (name, node.start_byte, node.end_byte, node.sexp())
        if nsig not in seen :
            seen.add(nsig)
            yield name, node

class SourceTree (object) :
    def __init__ (self, src, path=None, kind=None, nodes=[]) :
        if isinstance(src, str) :
            src = src.encode("utf-8")
        self.src = src
        self.path = path
        self.tree = parser.parse(src)
        self.root = self.tree.root_node
        self.nodes = list(nodes)
        self.kind = kind
    def __getitem__ (self, node) :
        return self.src[node.start_byte:node.end_byte].decode("utf-8")
    def __bool__ (self) :
        return bool(self.nodes)
    _dump_ignore = set("{}()[],;") | {"comment", "ERROR", "MISSING"}
    _dump_source = {"identifier"}
    def dump_all (self) :
        for node in self.nodes :
            if node.type not in self._dump_ignore :
                yield dump(node)
    def dump (self, node=None) :
        if node is None :
            node = self.root
        assert node.type not in self._dump_ignore
        tree = {"kind" : node.type}
        if node.type in self._dump_source or node.type.endswith("_literal") :
            txt = self[node]
            try :
                tree["val"] = ast.literal_eval(txt)
            except :
                tree["val"] = txt
        cursor = node.walk()
        if cursor.goto_first_child() :
            children = []
            while True :
                name = cursor.current_field_name()
                if name is not None :
                    tree[name] = self.dump(cursor.node)
                elif cursor.node.type not in self._dump_ignore :
                    children.append(self.dump(cursor.node))
                if not cursor.goto_next_sibling() :
                    break
            if children :
                tree["children"] = children
        return tree
    def errors (self, node=None) :
        if node is None :
            node = self.root
        if node.type in ("ERROR", "MISSING") :
            yield node
        else :
            for child in node.children :
                yield from self.errors(child)
    def errors_span (self, node=None) :
        return sum((n.end_byte - n.start_byte + 1 for n in self.errors(node)), 0)
    def __call__ (self, query, root=None) :
        if root is None :
            root = self.root
        match = collections.defaultdict(list)
        for name, node in _query_captures(query, root) :
            match[name].append(node)
        return dict(match)
    @classmethod
    def parse (cls, path, kind=None) :
        path = Path(path)
        src = path.read_text(**encoding)
        if kind not in ("static", "dynamic", None) :
            raise ValueError(f"unknown program kind: {kind!r}")
        if kind in ("static", None) :
            s_tree = cls("class StaticProgram { void setup() {\n" + src + "\n} }",
                         path=path,
                         kind="static")
            s_query = """(program
                          (class_declaration
                           body: (class_body
                                  (method_declaration
                                   body: (block
                                          (_) @node
            )))))"""
        if kind in ("dynamic", None) :
            d_tree = cls("class DynamicProgram {\n" + src + "\n}",
                         path=path,
                         kind="dynamic")
            d_query = """(program
                          (class_declaration
                           body: (class_body
                                  (_) @node
            )))"""
        if kind is None :
            if s_tree.errors_span() < d_tree.errors_span() :
                kind = "static"
            else :
                kind = "dynamic"
        if kind == "static" :
            tree, query = s_tree, s_query
        else :
            tree, query = d_tree, d_query
        tree.nodes = tuple(node for node in tree(query)["node"])
        return tree
    def discard (self, node) :
        with self.path.open("w", **encoding) as out :
            out.write(self.src[:node.start_byte].encode("utf-8"))
            out.write(self.src[node.end_byte:].encode("utf-8"))
        tree = self.parse(self.path, self.kind)
        if not tree.nodes :
            tree.path.unlink()
        return tree

def _tidy_node (node, src) :
    _src = src[node.start_byte:node.end_byte].decode("utf8")
    return " ".join(_src.split())

def tidy (sig) :
    _src = ("class DummyClass {\n" + sig + ";\n}").encode("utf-8")
    tree = parser.parse(_src)
    query = """(program
                (class_declaration
                 body: (class_body
                        (method_declaration
                         type: (_) @type
                         name: (_) @name
                         parameters: (_
                                      (formal_parameter)* @params
    )))))
    """
    match = {}
    for name, node in _query_captures(query, tree.root_node) :
        if name in ("type", "name") :
            match[name] = _tidy_node(node, _src)
        elif name == "params" :
            t = _tidy_node(node.child_by_field_name("type"), _src)
            n = _tidy_node(node.child_by_field_name("name"), _src)
            a = f"{t} {n}"
            if "params" not in match :
                match["params"] = a
            else :
                match["params"] += f", {a}"
    if "params" not in match :
        match["params"] = ""
    try :
        return "{type} {name}({params})".format(**match)
    except :
        raise ValueError(f"could not parse {sig!r}")
