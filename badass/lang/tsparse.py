import ast

from pathlib import Path
from tree_sitter import Language, Parser as TSParser

from colorama import Fore as F

from ._tslib import LANGS
from .. import tree, LabelledTree

class SourceFile (object) :
    def __init__ (self, src, path, tree, lang, clean) :
        self.src = src
        self.path = path
        self.tree = tree
        self.lang = lang
        self.clean = clean
        self.ast = self._dump_node()
    def _get_source (self, node) :
        return self.src[node.start_byte:node.end_byte].decode("utf-8")
    _dump_ignore = {"c" : (set("{}()[],;*\"'=\n")
                           | {"escape_sequence",
                              "return", "if", "else",
                              "while", "for", "case", "switch", "break"}),
                    "java" : set("{}()[],;")}
    _dump_clean = {"c" : {"comment", "ERROR", "MISSING"},
                    "java" : {"comment", "ERROR", "MISSING"}}
    def _dump_node (self, node=None) :
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
                elif ((ct := cursor.node.type)
                      and ct not in self._dump_ignore[self.lang]
                      and not (self.clean and ct in self._dump_clean[self.lang])) :
                    children.append(self._dump_node(cursor.node))
                if not cursor.goto_next_sibling() :
                    break
            if children :
                src = False
                dump["children"] = children
        if src :
            txt = self._get_source(node)
            try :
                val = ast.literal_eval(txt)
                assert isinstance(val, (int, float))
                dump["val"] = val
            except :
                dump["val"] = txt
        return dump
    def __str__ (self) :
        return str(self._label(self.path or "<string>", self.ast))
    @classmethod
    def _label (cls, label, node) :
        if isinstance(node, tree) :
            return LabelledTree(f"{label}: {F.GREEN}{node.kind}{F.RESET}",
                                [cls._label(key, val) for key, val in node.items()
                                 if key not in ("kind", "children")]
                                + [cls._label(f"{F.YELLOW}#{num}{F.RESET}", val)
                                   for num, val in enumerate(node.get("children", []))])
        elif isinstance(node, dict) :
            return LabelledTree(label, [cls._label(key, val) for key, val in node.items()])
        elif label == "val" :
            return LabelledTree(f"{F.BLUE}{label}{F.RESET}: {node}")
        else :
            return LabelledTree(f"{label}: {node}")

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
    def __call__ (self, src, path=None, clean=True) :
        if isinstance(src, str) :
            src = src.encode("utf-8")
        return SourceFile(src, path, self._parser.parse(src), self.lang, clean)
