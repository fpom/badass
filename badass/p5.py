import random, itertools, re, subprocess, pathlib, sys
from . import words

##
## clang
##

from clang.cindex import Index, Config, CursorKind
if not getattr(Config, "library_file", None) :
    ldconf = subprocess.run(["ldconfig", "-p"],
                            encoding="utf-8", capture_output=True).stdout
    _libclang = re.compile(r"^libclang(?:-[0-9.]+)?\.so(?:\.[0-9]+)?\b.*?=>\s+(.*)$")
    for line in (l.strip() for l in ldconf.splitlines()) :
        match = _libclang.match(line)
        if match :
            Config.set_library_file(match.group(1))
            break
    else :
        raise RuntimeError("could not load libclang")

_decl = set(getattr(CursorKind, c) for c in dir(CursorKind) if "DECL" in c)

def cdecl (include) :
    "extract all declared names from a #include"
    names = set()
    idx = Index.create()
    ast = idx.parse("include.c", unsaved_files=[("include.c", include)])
    for child in ast.cursor.get_children() :
        if child.is_definition() or child.kind in _decl :
            name = str(child.spelling)
            if name :
                names.add(name)
    return names

##
## cpp
##

_cpp_head = ""

def cpp (src, env={}, **var) :
    _env = dict(env)
    _env.update(var)
    src = subprocess.run(["cpp", "-P", "--traditional", "-C"]
                         + [f"-D{k}={v}" for k, v in _env.items()],
                         input=src, encoding="utf-8", capture_output=True).stdout
    return src.replace(_cpp_head, "")

_cpp_head = cpp("")

##
## helper classes
##

class String (str) :
    def __repr__ (self) :
        r = super().__repr__()
        return f"{self.__class__.__name__}({r})"

class Block (object) :
    def __init__ (self, name, cppenv={}, env={}, **more) :
        self.name = name
        self.cppenv = dict(cppenv)
        self.env = dict(env)
        for key, val in more.items() :
            setattr(self, key, val)
        self.out = []
    def __repr__ (self) :
        return f"<Block '{self.name}'>"
    def update (self, other, cppenv=True, env=True, out=True) :
        if cppenv :
            self.cppenv.update(other.cppenv)
        if env :
            self.env.update(other.env)
        if out :
            self.out.extend(other.out)

##
## main class
##

class PrePreProcessor (object) :
    def __init__ (self, *infiles, comment="//", include=[], **glet) :
        self.input = [open(f) if isinstance(f, str) else iter(f)
                      for f in reversed(infiles)]
        self.comment = comment
        self._glet = glet
        include = list(include)
        if "." not in include :
            include.append(".")
        self.include = [pathlib.Path(p) for p in include]
        self.stack = []
        self._cmd = {name[5:].replace("_", " ") : getattr(self, name)
                     for name in dir(self) if name.startswith("_cmd_")}
        self._let = {name[5:] : getattr(self, name)
                     for name in dir(self) if name.startswith("_let_")}
        self._ppp = {name[5:] : getattr(self, name)
                     for name in dir(self) if name.startswith("_ppp_")}
        _comment = re.escape(comment)
        _cmd = list(self._cmd)
        _cmd.sort(reverse=True, key=len)
        _command = "|".join(re.escape(c) for c in _cmd)
        self._cmd_re = re.compile(fr"^\s*{_comment}({_command})\b(.*?)$")
        ppp = self._do_ppp()
        self.ppp = ppp.replace("//#//", "")
        self.cpp = self._do_cpp(ppp)
    def save (self, stream=sys.stdout) :
        for key, val in self.top.cppenv.items() :
            stream.write(f"//let {key} = {val!r}\n")
        stream.write(self.ppp)
    def push (self, *l, **k) :
        if self.stack :
            env = dict(self.top.env)
            cppenv = dict(self.top.cppenv)
            env.update(k.pop("env", {}))
            cppenv.update(k.pop("cppenv", {}))
        else :
            env = k.pop("env", {})
            cppenv = k.pop("cppenv", {})
        self.stack.append(Block(*l, env=env, cppenv=cppenv, **k))
    def pop (self, name, *expected) :
        block = self.stack.pop(-1)
        exp = "/".join(f"'{e}'" for e in expected)
        assert block.name in expected, f"unexpected '{name}' ('{block.name}' expected {exp})"
        return block
    @property
    def top (self) :
        return self.stack[-1]
    def _find_file (self, path) :
        for base in self.include :
            test = base / path
            if test.exists() :
                return test
    def _do_ppp (self) :
        self.push(None, cppenv=self._glet)
        for name, method in sorted(self._ppp.items()) :
            method()
            assert len(self.stack) == 1, f"unclosed '{self.top.name}'"
            self.input = [iter(self.top.out)]
            self.top.out = []
        return "\n".join(itertools.chain.from_iterable(self.input))
    def _do_cpp (self, txt) :
        return cpp(txt, self.top.cppenv).replace("//#//", "")
    def _eval (self, expr) :
        env = dict(self.top.env)
        env.update(self._let)
        env.update(self.top.cppenv)
        return eval(expr, env)
    def _lines (self, accept, reject) :
        while self.input :
            try :
                line = next(self.input[-1]).rstrip()
            except StopIteration :
                self.input.pop(-1)
                continue
            match = self._cmd_re.match(line)
            if match :
                cmd, args = match.group(1), match.group(2).lstrip()
                assert cmd not in reject, f"unexpected '{cmd}'"
                if cmd in accept :
                    yield self._cmd[cmd], args
                else :
                    yield None, line
            else :
                yield None, line
    def _cmd_include (self, args) :
        self.input.append(open(self._find_file(args)))
    def _cmd_skip (self, args) :
        self.push("skip", keep=False)
    def _cmd_end_skip (self, args) :
        block = self.pop("end skip", "skip")
        self.top.update(block, out=False)
    def _cmd_shuffle (self, args) :
        self.push("shuffle")
    def _cmd_end_shuffle (self, args) :
        block = self.pop("end shuffle", "shuffle")
        random.shuffle(block.out)
        self.top.update(block)
    def _cmd_let (self, args) :
        self._do_let(args)
    def _1_cmd_let (self, args) :
        self.names.add(args.split("=", 1)[0].split("(", 1)[0].strip())
        self.top.out.append(f"{self.comment}let {args}")
    def _ppp_1 (self) :
        self._do_let = self._1_cmd_let
        self.names = set()
        for cmd, args in self._lines({"skip", "end skip",
                                      "let",
                                      "include",
                                      "shuffle", "end shuffle"},
                                     {}) :
            if cmd is not None :
                cmd(args)
            else :
                if args.startswith("#") :
                    if args.startswith("#include") :
                        self.names.update(cdecl(args))
                    args = "//#//" + args
                self.top.out.append(args)
        for name, wset in words.wlists.items() :
            self.top.env[name] = words.cut(wset) - self.names
    def _cmd_letdefault (self, args) :
        name, expr = args.split("=", 1)
        self.top.cppenv.setdefault(name.strip(), self._eval(expr.strip()))
    def _cmd_import (self, args) :
        exec(f"import {args}", self.top.env)
    def _cmd_from (self, args) :
        exec(f"from {args}", self.top.env)
    def _cmd_if (self, args, stop=False, name="if") :
        cond = not stop and self._eval(args)
        self.push(name, keep=cond, stop=(cond or stop))
    def _cmd_if_let (self, args) :
        cond = args in self.cppenv
        self.push("iflet", keep=cond, stop=cond)
    def _cmd_if_not_let (self, args) :
        cond = args not in self.cppenv
        self.push("ifnlet", keep=cond, stop=cond)
    def _cmd_else_if (self, args) :
        block = self._cmd_end_if(None, name="else if")
        self._cmd_if(args, stop=block.stop, name="else if")
    def _cmd_else (self, args) :
        block = self._cmd_end_if(None, name="else if")
        self._cmd_if(str(not block.keep), stop=block.stop, name="else")
    def _cmd_end_if (self, args, name="end if") :
        block = self.pop(name, "if", "if let", "if not let", "else", "else if")
        if block.keep :
            self.top.update(block)
        return block
    def _cmd_for (self, args) :
        _body = []
        for cmd, line in self._lines({"end for"}, {}) :
            if cmd is None :
                _body.append(line)
            else :
                break
        body = "\n".join(_body)
        names, expr = args.split(" in ", 1)
        unroll = []
        for t in self._eval(expr) :
            env = dict(self.top.env)
            env.update(self._let)
            env.update(self.top.cppenv)
            old = set(env)
            exec(f"{names} = {t!r}", env)
            unroll.extend(cpp(body, **{k : v for k, v in env.items()
                                       if k not in old
                                       and not k.startswith("_")}).splitlines())
        self.input.append(iter(unroll))
    def _cmd_end_for (self, args) :
        pass
    def _2_cmd_let (self, args) :
        name, expr = args.split("=", 1)
        self.top.cppenv[name.strip()] = self._eval(expr.strip())
    def _ppp_2 (self) :
        self._do_let = self._2_cmd_let
        for cmd, args in self._lines({"let",
                                      "letdefault",
                                      "import", "from",
                                      "for", "end for",
                                      "if", "if let", "if not let",
                                      "else", "else if", "end if"},
                                     {"skip", "end skip",
                                      "shuffle", "end shuffle"}) :
            if cmd is not None :
                cmd(args)
            else :
                self.top.out.append(args)
    def _let_randname (self, wds=None) :
        if wds is None :
            wds = self.top.env["english"]
        name = random.choice(list(sorted(wds)))
        wds.discard(name)
        return name
    def _let_randstring (self, *wlists, join=" ") :
        p = []
        for wds in wlists :
            w = random.choice(list(sorted(wds)))
            wds.discard(w)
            p.append(w)
        return String(join.join(p))
    def _let_string (self, val) :
        return String(str(val))
    def _let_randint (self, a, b, len=0, unique=False, fmt=("{", ", ", "}")) :
        if len :
            if unique :
                values = random.sample(range(a, b+1), len)
            else :
                values = [random.randint(a, b) for i in range(len)]
            if fmt :
                l, m, r = fmt
                return l + m.join(str(v) for v in values) + r
            else :
                return values
        else :
            return random.randint(a, b)
    def _let_choice (self, *args) :
        return random.choice(args)
    def _let_shufflestring (self, val) :
        l = list(str(val))
        random.shuffle(l)
        return String("".join(l))
    def _let_islet (self, name) :
        return name in self.top.cppenv

##
## user helper
##

def p5 (*infiles, comment="//", include=[], ret="ppp", **glet) :
    p = PrePreProcessor(*infiles, comment=comment, include=include, **glet)
    if ret == "cpp" :
        return p.cpp
    elif ret == "ppp" :
        return p.ppp
    elif ret == "let" :
        return p.cppenv
    else :
        raise ValueError("unsupported value for ret {ret!r},"
                         " expected 'cpp', 'ppp', or 'let'")
