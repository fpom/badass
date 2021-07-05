import sys, ast

from pathlib import Path

from tree_sitter import Language, Parser

import badass.lang

JAVA = Language(Path(badass.lang.__file__).parent / "tslib.so", "java")
parser = Parser()
parser.set_language(JAVA)

_dump_ignore = set("{}()[],;") | {"comment", "ERROR", "MISSING"}
_dump_source = {"identifier"}

def dump_node (node, src) :
    assert node.type not in _dump_ignore
    tree = {"kind" : node.type}
    if node.type in _dump_source or node.type.endswith("_literal") :
        txt = src[node.start_byte:node.end_byte].decode("utf-8")
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
                tree[name] = dump_node(cursor.node, src)
            elif cursor.node.type not in _dump_ignore :
                children.append(dump_node(cursor.node, src))
            if not cursor.goto_next_sibling() :
                break
        if children :
            tree["children"] = children
    return tree

def parse_static (src) :
    _src = ("class StaticProgram { void setup() {\n" + src + "\n} }").encode("utf-8")
    tree = parser.parse(_src)
    query = """(program
                (class_declaration
                 body: (class_body
                        (method_declaration
                         body: (block
                                (_) @statement
    )))))"""
    return [m[0] for m in JAVA.query(query).captures(tree.root_node)], _src

def parse_dynamic (src) :
    _src = ("class DynamicProgram {\n" + src + "\n}").encode("utf-8")
    tree = parser.parse(_src)
    query = """(program
                (class_declaration
                 body: (class_body
                        (_) @content
    )))"""
    return [m[0] for m in JAVA.query(query).captures(tree.root_node)], _src

def errors (node) :
    if node.type in ("ERROR", "MISSING") :
        yield node
    else :
        for child in node.children :
            yield from errors(child)

def errors_span (node) :
    return sum((node.end_byte - node.start_byte + 1 for node in errors(node)), 0)

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
    for node, name in JAVA.query(query).captures(tree.root_node) :
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
    return "{type} {name}({params})".format(**match)

def parse (src, kind=None) :
    if kind not in ("static", "dynamic", None) :
        raise ValueError(f"unknown program kind: {kind!r}")
    if kind in ("static", None) :
        s_nodes, s_src = parse_static(src)
    if kind in ("dynamic", None) :
        d_nodes, d_src = parse_dynamic(src)
    if kind is None :
        s_err = sum((errors_span(n) for n in s_nodes), 0)
        d_err = sum((errors_span(n) for n in d_nodes), 0)
        if s_err < d_err :
            kind = "static"
        else :
            kind = "dynamic"
    if kind == "static" :
        nodes, src = s_nodes, s_src
    else :
        nodes, src = d_nodes, d_src
    return {"kind" : f"{kind}_program",
            "children" : [dump_node(n, src) for n in nodes
                          if n.type not in _dump_ignore]}
