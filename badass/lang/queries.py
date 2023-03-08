"""Queries on AST for human beings

A Query is basically a list of items, built by simply passing it the items it
should hold:

>>> q = Q([
    {'kind': 'declaration',
     'type': {'kind': 'primitive_type', 'src': 'int'},
     'declarator': {'kind': 'init_declarator',
       'declarator': {'kind': 'identifier', 'src': 'a'},
       'value': {'kind': 'number_literal', 'src': '1'}}},
    {'kind': 'declaration',
     'type': {'kind': 'primitive_type', 'src': 'int'},
     'declarator': {'kind': 'init_declarator',
       'declarator': {'kind': 'identifier', 'src': 'b'},
       'value': {'kind': 'number_literal', 'src': '2'}}},
    {'kind': 'declaration',
     'type': {'kind': 'primitive_type', 'src': 'char'},
     'declarator': {'kind': 'init_declarator',
        'declarator': {'kind': 'pointer_declarator',
           'declarator': {'kind': 'identifier', 'src': 's'}},
        'value': {'kind': 'string_literal', 'src': '"hello"'}}},
    {'kind': 'expression_statement',
     'children': [{'kind': 'call_expression',
       'function': {'kind': 'identifier', 'src': 'printf'},
       'arguments': {'kind': 'argument_list',
         'children': [{'kind': 'string_literal', 'src': '"%s / %i / %i"'},
           {'kind': 'identifier', 'src': 's'},
           {'kind': 'identifier', 'src': 'a'},
           {'kind': 'identifier', 'src': 'b'}]}}]}])

It supports some methods of lists: `append`, `entend`, `__len__`, `__bool__`,
and `__iter__`.

Items may be selected with operator `q * pattern`. Trivial patterns are `True`
and `False` that select all, resp. no, items. If `pattern` is a string, it
selects all the dicts who have it as a key:

>>> list(q * "type")
[{'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'init_declarator',
   'declarator': {'kind': 'identifier', 'src': 'a'},
   'value': {'kind': 'number_literal', 'src': '1'}}},
 {'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'init_declarator',
   'declarator': {'kind': 'identifier', 'src': 'b'},
   'value': {'kind': 'number_literal', 'src': '2'}}},
 {'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'char'},
  'declarator': {'kind': 'init_declarator',
   'declarator': {'kind': 'pointer_declarator',
    'declarator': {'kind': 'identifier', 'src': 's'}},
   'value': {'kind': 'string_literal', 'src': '"hello"'}}}]

If `pattern` is a dict, it selects all the dicts that have the same key/val
as `pattern`:

>>> list(q * {"kind" : "expression_statement"})
[{'kind': 'expression_statement',
  'children': [{'kind': 'call_expression',
    'function': {'kind': 'identifier', 'src': 'printf'},
    'arguments': {'kind': 'argument_list',
     'children': [{'kind': 'string_literal', 'src': '"%s / %i / %i"'},
      {'kind': 'identifier', 'src': 's'},
      {'kind': 'identifier', 'src': 'a'},
      {'kind': 'identifier', 'src': 'b'}]}}]}]

Otherwise, `pattern` selects all the items that are equal to it.

Operator `**` is the recursive version of `*`: it selects either the items in
the query that match `pattern` or those that contain a sub-items that does.

>>> list(q ** {"kind" : "string_literal"})
[{'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'char'},
  'declarator': {'kind': 'init_declarator',
   'declarator': {'kind': 'pointer_declarator',
    'declarator': {'kind': 'identifier', 'src': 's'}},
   'value': {'kind': 'string_literal', 'src': '"hello"'}}},
 {'kind': 'expression_statement',
  'children': [{'kind': 'call_expression',
    'function': {'kind': 'identifier', 'src': 'printf'},
    'arguments': {'kind': 'argument_list',
     'children': [{'kind': 'string_literal', 'src': '"%s / %i / %i"'},
      {'kind': 'identifier', 'src': 's'},
      {'kind': 'identifier', 'src': 'a'},
      {'kind': 'identifier', 'src': 'b'}]}}]}]

Additionally, `Q.AND` and `Q.OR` allow to compose patterns to be used for a
selection with `*` or `**`.

Items can be also descended into: operator `/` will descend into each item
that matches a pattern:

>>> list(q / "type")
[{'kind': 'primitive_type', 'src': 'int'},
 {'kind': 'primitive_type', 'src': 'int'},
 {'kind': 'primitive_type', 'src': 'char'}]

(Note that the result is a list of matches, not a set, so it allows to count.)
And `//` the recursive version of `/`:

>>> list(q // {"kind" : "identifier"})
[{'kind': 'identifier', 'src': 'a'},
 {'kind': 'identifier', 'src': 'b'},
 {'kind': 'identifier', 'src': 's'},
 {'kind': 'identifier', 'src': 'printf'},
 {'kind': 'identifier', 'src': 's'},
 {'kind': 'identifier', 'src': 'a'},
 {'kind': 'identifier', 'src': 'b'}]

Then, intermediat matches can be pinned and retrieved back:

>>> list((q // {"kind" : "declaration"} >> "call")
...      / "declarator" * {"kind" : "identifier"} << "call")
[{'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'identifier', 'src': 'a'}},
 {'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'identifier', 'src': 'c'}}]

Operator `>>` pins the current items to name `call` so that they are
remembered while descending with `/`. But when descending with `/`, only those
pinned items that allow to do so are kept. The same occurs when selecting
with `*`. So, when `<<` is used to retrived the pinned items, they have been
filtered with `/` and `*`.

The example above could have been achieved with only `*` using:

>>> list(q // {"kind":"declaration", "declarator" : {"kind" : "identifier"}}))
[{'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'identifier', 'src': 'a'}},
 {'kind': 'declaration',
  'type': {'kind': 'primitive_type', 'src': 'int'},
  'declarator': {'kind': 'identifier', 'src': 'c'}}]

But this works only because we used `/` in the pinned version as we know
exactly how each level is nested. If we have used `//` then this could not
be expressed by a nested dict pattern.
"""

import operator, sys

from functools import reduce, partial
from collections import defaultdict
from itertools import chain
ichain = chain.from_iterable

from .. import LabelledTree, tree
from colorama import Fore as F

#
# printing AST
#

def ast2lt (label, node) :
    if isinstance(node, tree) :
        if location := "_range" in node :
            s, e = node._range
        return LabelledTree(f"{label}: {F.GREEN}{node.kind}{F.RESET}"
                            + (f" {F.WHITE}[{s}:{e}]{F.RESET}"
                               if location else ""),
                            [ast2lt(key, val) for key, val in node.items()
                             if key not in ("kind", "children")
                             and not key.startswith("_")]
                            + [ast2lt(f"{F.YELLOW}#{num}{F.RESET}", val)
                               for num, val in enumerate(node.get("children", []))])
    elif isinstance(node, dict) :
        return LabelledTree(label, [ast2lt(key, val) for key, val in node.items()])
    elif label == "src" :
        return LabelledTree(f"{F.BLUE}{node!r}{F.RESET}")
    elif node is ... :
        return LabelledTree(f"{F.RED}...{F.RESET}")
    else :
        return LabelledTree(f"{label}: {node}")

def ast2str (ast, head="<AST>") :
    return str(ast2lt(head, ast))

def print_ast (ast, head="<AST>") :
    print(ast2str(ast, head))

#
# match
#

def slice2range (s) :
    start = 0 if s.start is None else s.start
    stop = sys.maxsize if s.stop is None else s.stop
    step = 1 if s.step is None else s.step
    return range(start, stop, step)

class _QOP (object) :
    pass

class _BINQOP (_QOP) :
    def __init__ (self, op, patterns) :
        self.op = op
        self.patterns = patterns
    def __call__ (self, obj, match) :
        return reduce(self.op, (match(obj, p) for p in self.patterns))

class _UNAQOP (_QOP) :
    def __init__ (self, op, pattern) :
        self.op = op
        self.pattern = pattern
    def __call__ (self, obj, match) :
        return self.op(match(obj, self.pattern))

class Q (object) :
    "a list of items"
    def __init__ (self, matches=[], pinned={}) :
        self.m = []
        self.p = dict(pinned)
        self.extend(matches)
    def __repr__ (self) :
        return f"<{self.__class__.__name__}:{len(self)}+{len(self.p)}>"
    def __str__ (self) :
        t = tree(kind=f"{len(self.m)} matched, {len(self.p)} pinned",
                 children=self.m)
        if self.p :
            t.pinned = self.p
        return ast2str(t, "<MATCH>")
    def append (self, m) :
        self.m.append(m)
    def extend (self, matches) :
        for m in matches :
            self.append(m)
    def __len__ (self) :
        return len(self.m)
    def __bool__ (self) :
        return bool(self.m)
    def __iter__ (self) :
        return iter(self.m)
    def __and__ (self, other) :
        if self.p or other.p :
            raise NotImplementedError("cannot & queries with pins")
        right = set(map(id, other))
        def _keep (obj) :
            return id(obj) in right
        return Q(filter(_keep, self))
    def __or__ (self, other) :
        if self.p or other.p :
            raise NotImplementedError("cannot | queries with pins")
        left = set(map(id, self))
        def _keep (obj) :
            return id(obj) in left
        return Q(chain(self, filter(_keep, other)))
    def __sub__ (self, other) :
        if self.p or other.p :
            raise NotImplementedError("cannot | queries with pins")
        right = set(map(id, other))
        def _keep (obj) :
            return id(obj) not in right
        return Q(filter(_keep, self))
    def _match (self, obj, pat) :
        if isinstance(pat, _QOP) :
            return pat(obj, self._match)
        elif isinstance(pat, bool) :
            return pat
        elif pat is ... :
            return True
        elif isinstance(obj, dict) and isinstance(pat, str) :
            return pat in obj
        elif isinstance(obj, dict) and isinstance(pat, dict) :
            match = all(self._match(obj.get(k, None), v)
                        for k, v in pat.items() if k is not ...)
            if not match or ... not in pat :
                return match
            ell = pat[...]
            if ell is None :
                return len(obj) == len(pat) - 1
            elif ell is ... :
                return True
            elif isinstance(ell, int) :
                return len(obj) == len(pat) + ell - 1
            elif isinstance(ell, range) :
                return len(obj) - len(pat) + 1 in ell
            elif isinstance(ell, slice) :
                return len(obj) - len(pat) + 1 in slice2range(ell)
            else :
                raise TypeError(f"invalid selector for key '...': {ell!r}")
        elif isinstance(obj, list) and isinstance(pat, list) :
            if ... in pat :
                idx = pat.index(...)
                head, tail = pat[:idx], pat[idx+1:]
            elif len(obj) != len(pat) :
                return False
            else :
                head, tail = pat, []
            return (all(self._match(o, p) for o, p in zip(obj, head))
                    and all(self._match(o, p)
                            for o, p in zip(reversed(obj), reversed(tail))))
        elif isinstance(obj, list) and isinstance(pat, int) :
            return len(obj) == pat
        elif isinstance(obj, list) and isinstance(pat, range) :
            return len(obj) in pat
        elif isinstance(obj, list) and isinstance(pat, slice) :
            return len(obj) in slice2range(pat)
        else :
            return obj == pat
    def _pinned (self, op, pat) :
        return {key : new for key, old in self.p.items()
                if (new := [(m, q) for m, p in old if (q := op(p, pat))])}
    def __mul__ (self, pat) :
        "select the items that match pat"
        return Q(filter(partial(self._match, pat=pat), self),
                 self._pinned(operator.mul, pat))
    def __pow__ (self, pat) :
        "select the items that either match pat or have a descendant that does"
        def _pow (obj) :
            return self._match(obj, pat) or Q([obj]) // pat
        return Q(filter(_pow, self),
                 self._pinned(operator.pow, pat))
    def _children (self, obj, pat) :
        if isinstance(obj, dict) :
            if isinstance(pat, str) :
                if pat in obj :
                    return [obj[pat]]
            elif isinstance(pat, dict) :
                return list(Q(obj.values()) * pat)
            elif pat is ... :
                return list(obj.values())
            else :
                raise TypeError(f"invalid child selector {pat!r}")
        elif isinstance(obj, (list, tuple, set)) :
            return list(Q(obj) * pat)
        return []
    def __truediv__ (self, pat) :
        "select items' children that match pat"
        return Q(ichain(filter(partial(self._match, pat=pat), self)),
                 self._pinned(operator.truediv, pat))
    def __floordiv__ (self, pat) :
        "select items' descendants that match pat"
        def _child (obj) :
            def _iter (obj) :
               if isinstance(obj, (list, set, tuple)) :
                   return obj
               elif isinstance(obj, dict) :
                   return obj.values()
               else :
                   return []
            return chain(self._children(obj, pat),
                         Q(_iter(obj)) // pat)
        return Q(ichain(map(_child, self)),
                 self._pinned(operator.floordiv, pat))
    def __rshift__ (self, key) :
        self.p[key] = [(m, Q([m])) for m in self]
        return self
    def __lshift__ (self, key) :
        return Q([m for m, p in self.p.get(key, []) if p])
    @classmethod
    def AND (cls, *patterns) :
        "intersection of patterns"
        return _BINQOP(operator.and_, patterns)
    @classmethod
    def OR (cls, *patterns) :
        "union of patterns"
        return _BINQOP(operator.or_, patterns)
    @classmethod
    def NOT (cls, pattern) :
        "negation of a pattern"
        return _UNAQOP(operator.not_, pattern)
