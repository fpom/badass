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

# TODO:
# * implement __imul__, __ipow__, __itruediv__, and __ifloordiv__ to
#   perform exact match, eg Q *= {...} matches is Q * {...} and Q has no more
#   keys than {...}
# * implement negative matches __invert__, eg Q ~ {...} selects in Q all what
#   {...} does not match
# * can we have negative searches, and recursive negative search/match 

import operator

from functools import reduce
from collections import defaultdict
from itertools import chain

class _QOP (object) :
    def __init__ (self, op, patterns) :
        self.op = op
        self.patterns = patterns
    def __iter__ (self) :
        return iter(self.patterns)

class Q (object) :
    "a list of items"
    def __init__ (self, matches=[], pinned={}) :
        self.m = []
        self.p = dict(pinned)
        self.extend(matches)
    def __repr__ (self) :
        return f"<{self.__class__.__name__}:{len(self)}+{len(self.p)}>"
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
    def _match (self, obj, pat) :
        if isinstance(pat, _QOP) :
            return reduce(pat.op, (self._match(obj, p) for p in pat))
        elif pat in (True, False) :
            return pat
        elif pat is ... :
            return True
        elif isinstance(obj, dict) and isinstance(pat, str) :
            return pat in obj
        elif isinstance(obj, dict) and isinstance(pat, dict) :
            return all(self._match(obj.get(k, None), v) for k, v in pat.items())
        elif isinstance(obj, list) and isinstance(pat, list) :
            if ... in pat :
                idx = pat.index(...)
                head, tail = pat[:idx], pat[idx+1:]
            elif len(obj) != len(pat) :
                return False
            else :
                head, tail = pat, []
            return (all(self._match(o, p) for o, p in zip(obj, head))
                    and all(self._match(o, p) for o, p in zip(reversed(obj),
                                                              reversed(tail))))
        else :
            return obj == pat
    def _pinned (self, op, pat) :
        return {key : new for key, old in self.p.items()
                if (new := [(m, q) for m, p in old if (q := op(p, pat))])}
    def __mul__ (self, pat) :
        "select the items that match pat"
        matches = [m for m in self if self._match(m, pat)]
        pinned = self._pinned(operator.mul, pat)
        return Q(matches, pinned)
    def __pow__ (self, pat) :
        "select the items that either match pat or have a descendant that does"
        matches = [m for m in self if self._match(m, pat) or Q([m]) // pat]
        pinned = self._pinned(operator.pow, pat)
        return Q(matches, pinned)
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
        matches = [c for m in self for c in self._children(m, pat)]
        pinned = self._pinned(operator.truediv, pat)
        return Q(matches, pinned)
    def _iter (self, obj) :
       if isinstance(obj, (list, set, tuple)) :
           return obj
       elif isinstance(obj, dict) :
           return obj.values()
       else :
           return []
    def __floordiv__ (self, pat) :
        "select items' descendants that match pat"
        matches = [c for  m in self for c in
                   chain(self._children(m, pat), Q(self._iter(m)) // pat)]
        pinned = self._pinned(operator.floordiv, pat)
        return Q(matches, pinned)
    def __rshift__ (self, key) :
        self.p[key] = [(m, Q([m])) for m in self]
        return self
    def __lshift__ (self, key) :
        return Q([m for m, p in self.p.get(key, []) if p])
    @classmethod
    def AND (cls, *patterns) :
        "intersection of patterns"
        return _QOP(operator.and_, patterns)
    @classmethod
    def OR (cls, *patterns) :
        "union of patterns"
        return _QOP(operator.or_, patterns)
