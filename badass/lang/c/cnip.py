import subprocess, re, pathlib

_line = re.compile(r"^([|\s]*--)\s*(\w+)\s*"
                   r"<(\d+)?:?(\d+)?\.\.(\d+)?:?(\d+)?>"
                   r"\s*`?(.*?)`?$")

class cnip (object) :
    def __init__ (self, **attr) :
        self._attr = dict(attr)
    def dict (self) :
        d = {k : v for k, v in self._attr.items() if k != "root"}
        d["children"] = [c.dict() for c in d["children"]]
        return d
    def __getattr__ (self, key) :
        try :
            return self._attr[key]
        except KeyError :
            raise AttributeError(key)
    @property
    def c (self) :
        if "root" in self :
            return self.root.src[self.start_char:self.end_char+1]
        else :
            return self.src
    @classmethod
    def parse (cls, path, errors=False) :
        stdout = subprocess.check_output(["cnip", path, "--C-dump-AST"],
                                         stderr=subprocess.DEVNULL,
                                         encoding="utf-8",
                                         errors="replace")
        source = open(path).read()
        lines = list(l.rstrip() for l in stdout.splitlines() if l.rstrip())
        line = lines.pop(0)
        assert line == "TranslationUnit"
        root = cls(kind=line,
                   _indent="",
                   path=pathlib.Path(path),
                   src=source,
                   children=[])
        stack = [root]
        def _pop () :
            last = stack.pop(-1)
            del last._attr["_indent"]
        for line in lines :
            if match := _line.match(line) :
                indent, name, l1, c1, l2, c2, snippet = match.groups()
                node = cls(kind=name,
                           root=root,
                           start_line=int(l1 or 0),
                           end_line=int(l2 or 0),
                           start_char=int(c1 or 0),
                           end_char=int(c2 or 0),
                           snippet=snippet,
                           children=[],
                           _indent=indent)
                if indent == stack[-1]._indent :
                    _pop()
                    stack.append(node)
                    stack[-2].children.append(node)
                elif len(indent) > len(stack[-1]._indent) :
                    stack.append(node)
                    stack[-2].children.append(node)
                else :
                    while stack[-1]._indent != node._indent :
                        _pop()
                    _pop()
                    stack.append(node)
                    stack[-2].children.append(node)
            elif errors :
                raise ValueError(line)
        while stack :
            _pop()
        return root
