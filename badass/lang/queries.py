"""Queries on AST for human beings

# Query objects

A query is basically a list of items, built by simply passing it the items it
should hold:

>>> q = Q([
... {"a" : "A",
...  "b" : "B",
...  "c" : {"x" : "X"}},
... {"a" : "Aaaa",
...  "b" : "B"},
... {"a" : "A",
...  "c" : {"x" : "X"}},
... {"b" : "B",
...  "c" : {"x" : "Z"}}])
>>> q
<Q:4>

It supports some methods of lists: `append`, `entend`, `__len__`, `__bool__`,
`__iter__`, and `__getitem__`. It also supports `&`, `|`, and `-` sets
operations.

Note that `Q` objets are lists, i.e. they allow for repeated items, which makes
it possible to count the number of matches. And `&` and `|` implement sets
operation based on the ids of items (and not structural equality), which also
allows to count the number of matches without counting twice exactly the same.

Items in `Q` objects may be any Python objects, but mostly we are interested
in `dict` that implement AST, and `list` that may be found inside. Other types
may be collected while traversing AST.

# Selection

Items may be selected with operator `q * pattern`. Trivial patterns are `True`
and `False` that select all, resp. no, items. `...` is also a trivial pattern
matches anything but `None`. It as other uses as shown below.

## Matching `dict` values

If `pattern` is a string, it selects all the dicts who have it as a key:

>>> q * "a"
<Q:3>
>>> list(q * "a")
[{'a': 'A', 'b': 'B', 'c': {'x': 'X'}},
 {'a': 'Aaaa', 'b': 'B'},
 {'a': 'A', 'c': {'x': 'X'}}]

If `pattern` is a dict, it selects all the dicts that have the same key/val
as `pattern`:

>>> list(q * {"a" : ..., "b" : "B"})
[{'a': 'A', 'b': 'B', 'c': {'x': 'X'}},
 {'a': 'Aaaa', 'b': 'B'}]

As shown here, `...` acts as a wildcard to match any `dict` with a key `"a"`.
`...` may be used also as a key to specify what the `dict` is allowed to
contain on its other keys, in particular the number of other keys:

>>> list(q * {"a" : ... , "b" : "B", ... : 0})
[{'a': 'Aaaa', 'b': 'B'}]
>>> list(q * {"a" : ... , "b" : "B", ... : 1})
[{'a': 'A', 'b': 'B', 'c': {'x': 'X'}}]
>>> list(q * {"a" : ... , "b" : "B", ... : range(2)})
[{'a': 'A', 'b': 'B', 'c': {'x': 'X'}},
 {'a': 'Aaaa', 'b': 'B'}]

The value specified with key `...` can be:
 * an `int` to match exactly this number of other keys
 * a `range` to match any number of other keys within the range
 * a `slice` to specify a `range` without an upper bound 

## Matching lists

Items within a `Q` object may be lists also, in which case, they can be matched
with:
 * an `int`, a `range` or a `slice` to match wrt their length
 * another list to match their contents

>>> l = [[0], [0, 1], [0, 2], [0, 1, 0], [0, 1, 2, 0],
...      [1], [1, 2], [1, 2, 3]]
>>> list(Q(l) * 3)  # 3 items
[[0, 1, 0],
 [1, 2, 3]]
>>> list(Q(l) * range(2,4))  # 2 to 3 items
[[0, 1],
 [0, 2],
 [0, 1, 0],
 [1, 2],
 [1, 2, 3]]
>>> list(Q(l) * [0, True])  # two items, the first one being 0
[[0, 1],
 [0, 2]]
>>> list(Q(l) * [0, ..., 0]) # first and last being 0
[[0, 1, 0],
 [0, 1, 2, 0]]

## Matching other values

Other values are matched either with a trivial pattern or just compared using
equality. For instance above, we matched the ints in lists by comparing them
to either other ints or `...`.

# Recursive matching

Operator `**` is the recursive version of `*`: it selects either the items in
the query that match `pattern` or those that contain a sub-items that does.

>>> list(q ** {"x" : ...}) 
[{'a': 'A', 'b': 'B', 'c': {'x': 'X'}},
 {'a': 'A', 'c': {'x': 'X'}},
 {'b': 'B', 'c': {'x': 'Z'}}]

Additionally, `Q.AND`, `Q.OR` and `Q.NOT` allow to compose patterns to be
used for a selection with `*` or `**`.

# AST traversal

`dict` values can be traversed on:
 * a key: returns the associated value
 * `...`: returns all the values
 * a pattern suitable for `*`: returns all the values matching the pattern

>>> list(q / "c")
[{'x': 'X'},
 {'x': 'X'},
 {'x': 'Z'}]
>>> list(q / ...)
['A', 'B', {'x': 'X'}, 'Aaaa', 'B', 'A', {'x': 'X'}, 'B', {'x': 'Z'}]

We see here that the result is a list of matches, not a set, so it
allows to count.

`//` the recursive version of `/`:

>>> list(q // "x")
['X', 'X', 'Z']

# Pinning matches

Intermediate matches can be pinned and retrieved back:

>>> q = Q([{"a" : {"b" : {"c" : {"x" : "X"}}}},
...        {"a" : {"b" : {"c" : {"x" : "Z"}}}}])
>>> list(q // {"b" : ...}
[{'b': {'c': {'x': 'X'}}},
 {'b': {'c': {'x': 'Z'}}}]
>>> list(q // {"b" : ...} // {"x" : "X"})
[{'x': 'X'}]
>>> list((q // {"b" : ...} >> "match") // {"x" : "X"} << "match")
[{'b': {'c': {'x': 'X'}}}]

The first request searchs recursively all dicts with a key `"b"`. 
The second request searchs within the first match for dict `{"x" : "X"}`.
But doing so, we loose the result of the first match because we traversed its
items. In the third request, we use operator `>>` to pin the match to name
`"match"`, and later we use `<<` to call back this match that has been filtered
because of the second `//`. Note that we need parentheses to respect Python
operators precedence. Note also the `repr` of `Q` objects with pinned matches:

>>> q // {"b" : ...} >> "match"
<Q:2+1>

That is: `Q` object has 2 matches and 1 pin.

Sets operations are currently not supported for `Q` objects with pins.
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
        p = f"+{len(self.p)}" if self.p else ""
        return f"<{self.__class__.__name__}:{len(self)}{p}>"
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
    def __getitem__ (self, key) :
        return self.m[key]
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
            return obj is not None
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
            return (len(obj) >= len(pat)
                    and all(self._match(o, p) for o, p in zip(obj, head))
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
        return Q(ichain(map(partial(self._children, pat=pat), self)),
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
