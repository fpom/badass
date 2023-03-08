import ast, collections

from pathlib import Path
from tree_sitter import Language, Parser as TSParser, Node

from colorama import Fore as F

from .queries import Q, ast2str
from ._tslib import LANGS
from .. import tree, encoding

import badass.lang

#
# a single source file
#

class SourceFile (object) :
    LANG = "c"
    #
    # parsing
    #
    _language = {}
    _tsparser = {}
    @classmethod
    def parse (cls, src, path=None, clean=True, ellipsis=None, location=True) :
        parser = cls._mkparser()
        if isinstance(src, str) :
            src = src.encode(**encoding)
        return cls(src, path, parser.parse(src), clean, ellipsis, location)
    @classmethod
    def parse_file (cls, path, clean=True, ellipsis=None, location=True) :
        src = open(path, "rb").read()
        return cls.parse(src, path, clean, ellipsis, location)
    @classmethod
    def _mkparser (cls) :
        if cls.LANG not in cls._language :
            sopath = Path(badass.lang.__file__).parent / "tslib.so"
            cls._language[cls.LANG] = Language(sopath, cls.LANG)
        if cls.LANG not in cls._tsparser :
            cls._tsparser[cls.LANG] = TSParser()
            cls._tsparser[cls.LANG].set_language(cls._language[cls.LANG])
        return cls._tsparser[cls.LANG]
    #
    # source file
    #
    def __init__ (self, src, path, tree,
                  clean=True, ellipsis=None, location=True) :
        self.src = src
        self.path = path
        self.clean = clean
        self.ellipsis = ellipsis
        self.location= location
        self.ast = self._dump_node(tree.root_node)
    _dump_ignore = (set("{}()[],;*\"'=\n")
                    | {"escape_sequence",
                       "#include", "struct", "typedef",
                       "return", "if", "else",
                       "while", "for", "case", "switch", "break"})
    _dump_clean = {"comment", "ERROR", "MISSING"}
    def _dump_node (self, node) :
        "dump TreeSitter node a as tree"
        dump = tree(kind=node.type)
        if self.location :
            dump["_range"] = (node.start_byte, node.end_byte)
            dump["_path"] = self.path
        cursor = node.walk()
        src = True
        if cursor.goto_first_child() :
            children = []
            while True :
                name = cursor.current_field_name()
                if name is not None :
                    src = False
                    dump[name] = self._dump_node(cursor.node)
                elif (cursor.node.type == "ERROR"
                      and (sub := self._dump_node(cursor.node))
                      and len(sub.get("children", [])) == 1) :
                    return sub["children"][0]
                elif (self.ellipsis and cursor.node.type == "ERROR"
                      and self.ellipsis in self[node]) :
                    children.append(...)
                elif ((ct := cursor.node.type)
                      and ct not in self._dump_ignore
                      and not (self.clean and ct in self._dump_clean)) :
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
        return ast2str(self.ast, f"{F.MAGENTA}{self.path or '<STRING>'}{F.RESET}")
    def _get_range (self, obj) :
        if isinstance(obj, tuple) :
            return obj
        elif isinstance(obj, tree) :
            return tree._range
        elif isinstance(obj, Node) :
            return obj.start_byte, obj.end_byte
        else :
            raise ValueError(f"invalid range {obj!r}")
    def __getitem__ (self, obj) :
        "get source code for a node"
        start_byte, end_byte = self._get_range(obj)
        return self.src[start_byte:end_byte].decode(**encoding)
    def __delitem__ (self, obj) :
        "delete source code for a node"
        start_byte, end_byte = self._get_range(obj)
        src = self.src[:start_byte] + self.src[end_byte:]
        self._update(src)
    def __setitem__ (self, obj, src) :
        "replace source code for a node"
        start_byte, end_byte = self._get_range(obj)
        if isinstance(src, str) :
            src = src.encode(**encoding)
        src = self.src[:start_byte] + src + self.src[end_byte:]
        self._update(src)
    def comment (self, obj, start, end="") :
        start_byte, end_byte = self._get_range(obj)
        chunks = [self.src[:start_byte].decode(**encoding)]
        for line in self[start_byte, end_byte].splitlines(keepends=True) :
            head = line.rstrip()
            tail = line[len(head):]
            chunks.append(f"{start}{head}{end}{tail}")
        chunks.append(self.src[end_byte:].decode(**encoding))
        self._update("".join(chunks).encode(**encoding))
    def _update (self, src) :
        if self.path :
            with open(self.path, "w", **encoding) as out :
                out.write(src.decode(**encoding))
        tree = self.parse(src, self.path, self.clean, self.ellipsis, self.location)
        self.src = src
        self.ast = tree.ast

#
# a collection of source files
#

class SourceTree (object) :
    LANG = "c"
    GLOB = ["*.c", "*.h"]
    COMMENT = ["/*", "*/"]
    ELLIPSIS = "@"
    #
    # content management
    #
    def __init__ (self, root) :
        self.root = Path(root)
        self.src = {}
        todo = [self.root]
        while todo :
            path = todo.pop()
            for glob in self.GLOB :
                for child in path.glob(glob) :
                    if child.is_dir() :
                        todo.append(child)
                    else :
                        self.add_path(child)
    def __repr__ (self) :
        return f"<SourceTree {self.root}:{len(self.src)}>"
    def __str__ (self) :
        return ast2str({f"{F.MAGENTA}{p}{F.RESET}" : s.ast for p, s in self.src.items()} ,
                       f"{F.MAGENTA}{self.root}{F.WHITE}/...{F.RESET}")
    def add_path (self, path) :
        sf = SourceFile.parse_file(path)
        path = str(path.relative_to(self.root))
        self.src[path] = sf
    def add_source (self, src, path) :
        if isinstance(src, str) :
            src = src.encode(**encoding)
        path = self.root / path
        with open(path, "wb") as out :
            out.write(src)
        self.add_path(path)
    def __getitem__ (self, ast) :
        return self.src[ast._path][ast]
    def __setitem__ (self, ast, src) :
        self.src[ast._path][ast] = src
    def __delitem__ (self, ast) :
        del self.src[ast._path][ast]
    def comment (self, ast) :
        self.src[ast._path].comment(ast, *self.COMMENT)
    #
    # patterns and queries
    #
    @classmethod
    def compile_pre (cls, src) :
        return src
    @classmethod
    def compile_post (cls, ast) :
        if ast.kind == "translation_unit" :
            return ast.children[0]
        else :
            return ast
    @classmethod
    def compile_pattern (cls, pat, ellipsis="...") :
        txt = cls.compile_pre(pat.replace(ellipsis, cls.ELLIPSIS))
        src = SourceFile.parse(txt,
                               location=False,
                               ellipsis=cls.ELLIPSIS)
        return cls.compile_post(src.ast)
    A = Q.AND
    O = Q.OR
    N = Q.NOT
    @property
    def Q (self) :
        """a query object that matches all the AST in the source tree"""
        return Q([st.ast for st in self.src.values()])
    def match (self, first, *others, debug=0, ellipsis="...") :
        last = len(others)
        prev = self.Q
        for num, pat in enumerate((first,) + others) :
            if isinstance(pat, str) :
                pat = self.compile_pattern(pat, ellipsis)
            if debug >= 1 :
                print_ast(pat, f"{F.CYAN}<PATTERN #{num}>{F.RESET}")
            prev = prev // pat
            if (debug >= 2 and num == last) or debug >= 3 :
                for n, match in enumerate(prev) :
                    print_ast(match, f"{F.MAGENTA}<MATCH #{n}>{F.RESET}")
            elif debug >= 1 :
                print(f"{F.MAGENTA}<MATCHED {len(prev)}>{F.RESET}")
        return prev
