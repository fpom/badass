import re, itertools

from functools import reduce
from operator import xor, or_, and_

from jsonpath_ng.ext import parse as jp_parse

##
##
##

def _h (obj) :
    if isinstance(obj, (str, int, float)) :
        return hash(obj)
    elif isinstance(obj, (list, tuple, set)) :
        hcn = _h(obj.__class__.__name__)
        return hash(tuple(map(_h, obj))) ^ hcn
    elif isinstance(obj, dict) :
        hcn = _h(obj.__class__.__name__)
        return reduce(xor, (hash((k, _h(v))) for k, v in obj.items()), hcn)
    else :
        return hash(obj)

class hdict (dict) :
    def __init__ (self, *l, **k) :
        super().__init__(*l, **k)
        self.h = None
    def __hash__ (self) :
        if self.h is None :
            self.h = _h(self)
        return self.h

class hlist (list) :
    def __init__ (self, *l, **k) :
        super().__init__(*l, **k)
        self.h = None
    def __hash__ (self) :
        if self.h is None :
            self.h = _h(self)
        return self.h

def h (obj) :
    if isinstance(obj, dict) :
        return hdict(obj)
    elif isinstance(obj, list) :
        return hlist(obj)
    else :
        return obj

class _TQL_OP (object) :
    def __init__ (self, op, patterns) :
        self.op = op
        self.patterns = patterns
    def __iter__ (self) :
        return iter(self.patterns)

class TQL (object) :
    def __init__ (self, matches=[]) :
        self.m = set()
        self.update(matches)
    def add (self, m) :
        self.m.add(h(m))
    def update (self, matches) :
        for m in matches :
            self.add(m)
    def __len__ (self) :
        return len(self.m)
    def __bool__ (self) :
        return bool(self.m)
    def __iter__ (self) :
        return iter(self.m)
    def __or__ (self, other) :
        return TQL(self.m | other.m)
    def __and__ (self, other) :
        return TQL(self.m & other.m)
    def __sub__ (self, other) :
        return TQL(self.m - other.m)
    def __eq__ (self, other) :
        return self.m == set(other)
    def __ne__ (self, other) :
        return self.m != set(other)
    def __le__ (self, other) :
        return self.m <= set(other)
    def __lt__ (self, other) :
        return self.m < set(other)
    def __ge__ (self, other) :
        return self.m >= set(other)
    def __gt__ (self, other) :
        return self.m > set(other)
    @classmethod
    def _match (cls, obj, pat) :
        if isinstance(pat, _TQL_OP) :
            return reduce(pat.op, (cls._match(obj, p) for p in pat))
        elif isinstance(obj, dict) and isinstance(pat, str) :
            return pat in obj
        elif isinstance(obj, dict) and isinstance(pat, dict) :
            return all(cls._match(obj.get(k, None), v) for k, v in pat.items())
        elif isinstance(obj, list) and isinstance(pat, list) :
            return (len(obj) == len(pat)
                    and all(cls._match(v, p) for v, p in zip(obj, pat)))
        elif isinstance(obj, list) and isinstance(pat, int) :
            return 0 <= pat < len(obj)
        else :
            return obj == pat
    def __mul__ (self, pat) :
        return TQL(m for m in self if self._match(m, pat))
    def __pow__ (self, pat) :
        match = self * pat
        match.update(m for m in self if TQL([m]) // pat)
        return match
    def __truediv__ (self, pat) :
        if isinstance(pat, _TQL_OP) :
            return reduce(pat.op, (self / p for p in pat))
        match = TQL()
        for m in self :
            if isinstance(m, dict) :
                if isinstance(pat, str) :
                    if pat in m :
                        match.add(m[pat])
                elif isinstance(pat, dict) :
                    match.update(v for v in m.values() if self._match(v, pat))
                else :
                    raise TypeError(f"invalid child selector {pat!r}")
            elif isinstance(m, list) :
                if isinstance(pat, dict) :
                    match.update(v for v in m if self._match(v, pat))
                elif isinstance(pat, list) :
                    if self._match(m, pat) :
                        match.add(m)
                elif isinstance(pat, int) :
                    if 0 <= pat < len(m) :
                        match.add(m)
                else :
                    raise TypeError(f"invalid child selector {pat!r}")
            else :
                pass # cannot descend into other nodes
        return match
    def __floordiv__ (self, other) :
        match = self / other
        for m in self :
            if isinstance(m, list) :
                match.update(TQL(m) // other)
            elif isinstance(m, dict) :
                match.update(TQL(m.values()) // other)
        return match
    @classmethod
    def AND (cls, *patterns) :
        return _TQL_OP(and_, patterns)
    @classmethod
    def OR (cls, *patterns) :
        return _TQL_OP(or_, patterns)
    _ast_call = "method_invocation"
    @classmethod
    def CALL (cls, name=None) :
        if name is None :
            return {"kind" : cls._ast_call,
                    "name" : {"kind" : "identifier"}}
        else :
            return {"kind" : cls._ast_call,
                    "name" : {"kind" : "identifier",
                              "val" : name}}
    _ast_loop = ("for", "while", "do")
    @classmethod
    def LOOP (cls, *kind) :
        return cls.STMT(*(kind or cls._ast_loop))
    _ast_cond = ("if", "switch")
    @classmethod
    def COND (cls, *kind) :
        return cls.STMT(*(kind or cls._ast_cond))
    @classmethod
    def STMT (cls, *kind) :
        return {"kind" : cls.OR(*(f"{k.lower()}_statement" for k in kind))}
    def func (self, name=None, ret=None, params=None, recursive=None) :
        pat = {"kind" : "method_declaration"}
        if name is not None :
            pat["name"] = {"kind" : "identifier",
                           "val": name}
        if ret == "void" :
            pat["type"] = {"kind" : "void_type"}
        elif isinstance(ret, str) :
            pat["type"] = {"kind" : "integral_type",
                           "children" : [{"kind" : ret}]}
        if params is not None :
            pat["parameters"] = {
                "kind" : "formal_parameters",
                "children" : [
                    {"kind" : "formal_parameter",
                     "type" : {
                         "kind" : "integral_type",
                         "children" : [{"kind" : p}]}}
                    for p in params]}
        match = self // pat
        if recursive is None :
            return match
        elif recursive :
            return TQL([m for m in match
                        if TQL([m]) // self.CALL(m["name"]["val"])])
        else :
            return TQL([m for m in match
                        if not (TQL([m]) // self.CALL(m["name"]["val"]))])

##
##
##

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
    patt = parse(pattern)
    for match in patt.find(ast) :
        yield match.value

