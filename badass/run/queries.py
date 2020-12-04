import re, itertools

from jsonpath_ng.ext import parse as jp_parse

_parse_cache = {}

def parse (pattern) :
    if pattern not in _parse_cache :
        _parse_cache[pattern] = jp_parse(pattern)
    return _parse_cache[pattern]

_macro = re.compile("\{[^\}]+\}")

def expand (expr, lang) :
    macros = [m.group()[1:-1] for m in _macro.finditer(expr)]
    expand = [lang.MACROS[m] for m in macros]
    for choice in itertools.product(*expand) :
        repl = dict(zip(macros, choice))
        yield expr.format(**repl)

def query (pattern, ast) :
    exp = parse(pattern)
    for match in exp.find(ast) :
        yield match.value
