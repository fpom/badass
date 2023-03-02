import ast, collections

from pathlib import Path
from tree_sitter import Language, Parser as TSParser

from colorama import Fore as F

from .queries import Q
from ._tslib import LANGS
from .. import tree, LabelledTree, encoding

class SourceFile (object) :
    LANG = None
    #
    # parsing
    #
    _language = {}
    _tsparser = {}
    @classmethod
    def parse (cls, src, path=None, clean=True, ellipsis=None, lang=None) :
        if lang is None :
            lang = cls.LANG
        lang, parser = cls._mkparser(lang)
        if isinstance(src, str) :
            src = src.encode(**encoding)
        return cls(src, path, parser.parse(src), clean, ellipsis, lang=lang)
    @classmethod
    def parse_file (cls, path, clean=True, ellipsis=None, lang=None) :
        src = open(path, "rb").read()
        return cls.parse(src, path, clean, ellipsis, lang=lang)
    @classmethod
    def _mkparser (cls, lang) :
        if lang is None :
            lang = cls.LANG
        if lang is None :
            raise ValueError("language should be specified")
        lang = lang.lower()
        if lang not in LANGS :
            raise ValueError(f"language {lang} is not supported")
        if lang not in cls._language :
            cls._language[lang] = Language(Path(__file__).parent / "tslib.so", lang)
        if lang not in cls._tsparser :
            cls._tsparser[lang] = TSParser()
            cls._tsparser[lang].set_language(cls._language[lang])
        return lang, cls._tsparser[lang]
    #
    # source file
    #
    def __init__ (self, src, path, tree, clean, ellipsis=None, lang=None) :
        if lang is None :
            lang = self.LANG
        self.src = src
        self.path = path
        self.tree = tree
        self.lang = lang
        self.clean = clean
        self.ellipsis = ellipsis
        self.ast = self._dump_node()
    _dump_ignore = {"c" : (set("{}()[],;*\"'=\n")
                           | {"escape_sequence",
                              "#include", "struct", "typedef",
                              "return", "if", "else",
                              "while", "for", "case", "switch", "break"}),
                    "java" : set("{}()[],;")}
    _dump_clean = {"c" : {"comment", "ERROR", "MISSING"},
                    "java" : {"comment", "ERROR", "MISSING"}}
    def _dump_node (self, node=None) :
        "dump node a as tree"
        if node is None :
            node = self.tree.root_node
        dump = tree(kind=node.type)
        cursor = node.walk()
        src = True
        if cursor.goto_first_child() :
            children = []
            while True :
                name = cursor.current_field_name()
                if name is not None :
                    src = False
                    dump[name] = self._dump_node(cursor.node)
                elif (self.ellipsis and cursor.node.type == "ERROR"
                      and self.ellipsis in self[node]) :
                    children.append(...)
                elif ((ct := cursor.node.type)
                      and ct not in self._dump_ignore[self.lang]
                      and not (self.clean and ct in self._dump_clean[self.lang])) :
                    children.append(self._dump_node(cursor.node))
                if not cursor.goto_next_sibling() :
                    break
            if children :
                if self.ellipsis and children.count(...) > 1 :
                    raise ValueError("too many ellipsis")
                src = False
                dump["children"] = children
        if src :
            txt = self[node]
            if txt != dump.kind :
                dump["src"] = txt
        return dump
    def __str__ (self) :
        return str(self._str(self.path or "<string>", self.ast))
    @classmethod
    def _str (cls, label, node) :
        if isinstance(node, tree) :
            return LabelledTree(f"{label}: {F.GREEN}{node.kind}{F.RESET}",
                                [cls._str(key, val) for key, val in node.items()
                                 if key not in ("kind", "children")]
                                + [cls._str(f"{F.YELLOW}#{num}{F.RESET}", val)
                                   for num, val in enumerate(node.get("children", []))])
        elif isinstance(node, dict) :
            return LabelledTree(label, [cls._str(key, val) for key, val in node.items()])
        elif label == "src" :
            return LabelledTree(f"{F.BLUE}{label}{F.RESET}: {node}")
        elif node is ... :
            return LabelledTree(f"{F.RED}...{F.RESET}")
        else :
            return LabelledTree(f"{label}: {node}")
    def __getitem__ (self, node) :
        "get source code for a node"
        return self.src[node.start_byte:node.end_byte].decode(**encoding)
    def __delitem__ (self, node) :
        "delete source code for a node"
        src = self.src[:node.start_byte] + self.src[node.end_byte:]
        self._update(src)
    def __setitem__ (self, node, src) :
        "replace source code for a node"
        if isinstance(src, str) :
            src = src.encode(**encoding)
        src = self.src[:node.start_byte] + src + self.src[node.end_byte:]
        self._update(src)
    def comment (self, node, start, end="") :
        chunks = [self.src[:node.start_byte].decode(**encoding)]
        for line in self[node].splitlines(keepends=True) :
            head = line.rstrip()
            tail = line[len(head):]
            chunks.append(f"{start}{head}{end}{tail}")
        chunks.append(self.src[node.end_byte:].decode(**encoding))
        self._update("".join(chunks).encode(**encoding))
    def _update (self, src) :
        if self.path :
            with open(self.path, "w", **encoding) as out :
                out.write(src.decode(**encoding))
        tree = self.parse(src, self.path, self.clean, lang=self.lang)
        self.src = src
        self.tree = tree.tree
        self.ast = self._dump_node()
    #
    # TreeSitter queries
    #
    def tsq (self, query, root=None) :
        "run a TreeSitter query on a node (or root) and return captured nodes"
        if root is None :
            root = self.tree.root_node
        match = collections.defaultdict(list)
        seen = set()
        for node, name in self._language[self.lang].query(query).captures(root) :
            nsig = (name, node.start_byte, node.end_byte, node.sexp())
            if nsig not in seen :
                seen.add(nsig)
                match[name].append(node)
        return dict(match)

def print_ast (ast, head="<AST>") :
    print(SourceFile._str(head, ast))

class SourceTree (object) :
    LANG = None
    GLOB = ["*.c", "*.h"]
    DECL = {"func" : "(function_definition) @func",
            "type" : "(type_definition) @type"}
    COMMENT = ["/*", "*/"]
    def __init__ (self, root, lang=None) :
        if lang is None :
            lang = self.LANG
        self.lang = lang
        self.root = Path(root)
        self.src = {}
        self.obj = {}
        todo = [self.root]
        while todo :
            path = todo.pop()
            for glob in self.GLOB :
                for child in path.glob(glob) :
                    if child.is_dir() :
                        todo.append(child)
                    else :
                        self.add_path(child)
    def add_path (self, path) :
        sf = SourceFile.parse_file(path, lang=self.lang)
        path = str(path.relative_to(self.root))
        self.src[path] = sf
        for decl, query in self.DECL.items() :
            handler = getattr(self, f"get_{decl}_decl")
            for match in sf.tsq(query).get(decl, []) :
                name, node = handler(sf, match)
                self.obj[name] = path, node
    def get_func_decl (self, sf, node) :
        match = sf.tsq("(_ declarator: (_ declarator: (_) @name))", node)
        return sf[match["name"][0]], node
    def get_type_decl (self, sf, node) :
        match = sf.tsq("(_ (type_identifier) @name)", node)
        return sf[match["name"][0]], node
    def add_source (self, src, path) :
        if isinstance(src, str) :
            src = src.encode(**encoding)
        path = self.root / path
        with open(path, "wb") as out :
            out.write(src)
        self.add_path(path)
    def del_decl (self, name) :
        if name not in self.obj :
            return
        path, node = self.obj.pop(name)
        self.src[path].comment(node, *self.COMMENT)
    A = Q.AND
    O = Q.OR
    @property
    def Q (self) :
        """a query object that matches all the AST in the source tree"""
        return Q([st.ast for st in self.src.values()])
    def _filter_pattern (self, pat) :
        return self._filter_pattern_src(pat["children"][0])
    def _filter_pattern_src (self, pat) :
        if not isinstance(pat, dict) :
            return pat
        for val in pat.values() :
            if isinstance(val, dict) :
                self._filter_pattern_src(val)
            elif isinstance(val, list) :
                for item in val :
                    self._filter_pattern_src(item)
        return pat
    ELLIPSIS = "@"
    def has (self, pat, debug=False, ellipsis="...") :
        src = SourceFile.parse(pat.replace(ellipsis, self.ELLIPSIS),
                               lang=self.lang, ellipsis=self.ELLIPSIS)
        ast = self._filter_pattern(src.ast)
        if debug :
            print_ast(ast, "<pattern>")
        return self.Q // ast
