import ast

from pathlib import Path
from tree_sitter import Language, Parser as TSParser

from ._tslib import LANGS

class SourceFile (object) :
    def __init__ (self, src, path, tree, lang) :
        self.src = src
        self.path = path
        self.tree = tree
        self.lang = lang
        self.ast = self._dump_node()
    def _get_source (self, node) :
        return self.src[node.start_byte:node.end_byte].decode("utf-8")
    _dump_ignore = {"c" : (set("{}()[],;*\"'=")
                           | {"comment", "ERROR", "MISSING",
                              "escape_sequence", "\n", "#include",
                              "return", "if", "else",
                              "while", "for", "case", "switch", "break"}),
                    "java" : (set("{}()[],;")
                              | {"comment", "ERROR", "MISSING"})}
    def _dump_node (self, node=None) :
        if node is None :
            node = self.tree.root_node
        tree = {"kind" : node.type}
        cursor = node.walk()
        src = True
        if cursor.goto_first_child() :
            children = []
            while True :
                name = cursor.current_field_name()
                if name is not None :
                    src = False
                    tree[name] = self._dump_node(cursor.node)
                elif cursor.node.type not in self._dump_ignore[self.lang] :
                    children.append(self._dump_node(cursor.node))
                if not cursor.goto_next_sibling() :
                    break
            if children :
                src = False
                tree["children"] = children
        if src :
            txt = self._get_source(node)
            try :
                val = ast.literal_eval(txt)
                assert isinstance(val, (int, float))
                tree["val"] = val
            except :
                tree["val"] = txt
        return tree

class Parser (object) :
    _lang = {}
    def __init__ (self, lang) :
        lang = lang.lower()
        if lang not in LANGS :
            raise ValueError(f"language {lang} is not supported")
        self.lang = lang
        if lang not in self._lang :
            self._lang[lang] = Language(Path(__file__).parent / "tslib.so", lang)
        self._parser = TSParser()
        self._parser.set_language(self._lang[lang])
    def __call__ (self, src, path=None) :
        if isinstance(src, str) :
            src = src.encode("utf-8")
        return SourceFile(src, path, self._parser.parse(src), self.lang)
