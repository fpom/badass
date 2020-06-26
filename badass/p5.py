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

class If (object) :
    def __init__ (self, txt, cond, stop) :
        self.txt = txt
        self.cond = cond
        self.stop = stop
    def __str__ (self) :
        return self.txt
    def __eq__ (self, other) :
        return self.txt == str(other)

class String (str) :
    def c (self) :
        return '"' + "".join(c if c != '"' else "\\" + c for c in self) + '"'
    def __repr__ (self) :
        r = super().__repr__()
        return f"{self.__class__.__name__}({r})"

##
## main class
##

class PrePreProcessor (object) :
    def __init__ (self, *infiles, comment="//", include=[], **glet) :
        self.input = [open(f) if isinstance(f, str) else iter(f)
                      for f in reversed(infiles)]
        self.output = [[]]
        self.comment = comment
        include = list(include)
        if "." not in include :
            include.append(".")
        self.include = [pathlib.Path(p) for p in include]
        self.stack = []
        self.env = {}
        self._glet = dict(glet)
        self._cmd = {name[5:].replace("_", " ") : getattr(self, name)
                     for name in dir(self) if name.startswith("_cmd_")}
        self._let = {name[5:] : getattr(self, name)
                     for name in dir(self) if name.startswith("_let_")}
        self._ppp = {name[5:] : getattr(self, name)
                     for name in dir(self) if name.startswith("_ppp_")}
        self.env.update(self._let)
        _comment = re.escape(comment)
        _cmd = list(self._cmd)
        _cmd.sort(reverse=True, key=len)
        _command = "|".join(re.escape(c) for c in _cmd)
        self._cmd_re = re.compile(fr"^\s*{_comment}({_command})\b(.*?)$")
        ppp = self._do_ppp()
        self.ppp = ppp.replace("//#//", "")
        self.cpp = self._do_cpp(ppp)
    def save (self, stream=sys.stdout) :
        for key, val in self.cppenv.items() :
            stream.write(f"//let {key} = {val!r}\n")
        stream.write(self.ppp)
    def _find_file (self, path) :
        for base in self.include :
            test = base / path
            if test.exists() :
                return test
    def _do_ppp (self) :
        for name, method in sorted(self._ppp.items()) :
            method()
            self.input = [iter(l) for l in self.output if l]
            self.output = [[]]
        return "\n".join(itertools.chain.from_iterable(self.input))
    def _do_cpp (self, txt) :
        return cpp(txt, self.cppenv).replace("//#//", "")
    def _eval (self, expr) :
        env = self.env.copy()
        env.update(self.cppenv)
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
    def _cmd_let (self, args) :
        if self.cppenv is None :
            # first pass
            self.names.add(args.split("=", 1)[0].strip())
            self.output[-1].append(f"{self.comment}let {args}")
        else :
            # second pass
            name, expr = args.split("=", 1)
            self.cppenv[name.strip()] = self._eval(expr.strip())
    def _cmd_include (self, args) :
        self.input.append(open(self._find_file(args)))
    def _cmd_skip (self, args) :
        self.stack.append("skip")
        self.output.append([])
    def _cmd_end_skip (self, args) :
        cmd = self.stack.pop(-1)
        assert cmd == f"skip", f"unexpected 'end skip' (unmatched '{cmd}')"
        self.output.pop(-1)
    def _cmd_shuffle (self, args) :
        self.stack.append("shuffle")
        self.output.append([])
    def _cmd_end_shuffle (self, args) :
        cmd = self.stack.pop(-1)
        assert cmd == f"shuffle", f"unexpected 'end shuffle' (unmatched '{cmd}')"
        d = self.output.pop(-1)
        random.shuffle(d)
        self.output[-1].extend(d)
    def _ppp_1 (self) :
        self.cppenv = None # first pass
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
                self.output[-1].append(args)
        for name, wset in words.wlists.items() :
            self.env[name] = words.cut(wset) - self.names
        self.cppenv = self._glet # second pass
    def _cmd_letdefault (self, args) :
        name, expr = args.split("=", 1)
        self.cppenv.setdefault(name.strip(), self._eval(expr.strip()))
    def _cmd_import (self, args) :
        exec(f"import {args}", self.env)
    def _cmd_from (self, args) :
        exec(f"from {args}", self.env)
    def _cmd_if (self, args, stop=False, name="if") :
        cond = not stop and self._eval(args)
        self.stack.append(If(name, cond, cond or stop))
        self.output.append([])
    def _cmd_iflet (self, args) :
        cond = args in self.cppenv
        self.stack.append(If("iflet", cond, cond))
        self.output.append([])
    def _cmd_ifnlet (self, args) :
        cond = args not in self.cppenv
        self.stack.append(If("ifnlet", cond, cond))
        self.output.append([])
    def _cmd_elif (self, args) :
        cmd = self._cmd_end_if("", "elif")
        self._cmd_if(args, stop=cmd.stop, name="endif")
    def _cmd_end_if (self, args, name="end if") :
        cmd = self.stack.pop(-1)
        assert isinstance(cmd, If), "unexpected '{name}' (unmatched '{cmd}')"
        out = self.output.pop(-1)
        if cmd.cond :
            self.output[-1].extend(out)
        return cmd
    def _ppp_2 (self) :
        for cmd, args in self._lines({"let",
                                      "letdefault",
                                      "import", "from",
                                      "if", "iflet", "ifnlet", "elif", "end if"},
                                     {"skip", "end skip",
                                      "shuffle", "end shuffle"}) :
            if cmd is not None :
                cmd(args)
            else :
                self.output[-1].append(args)
    def _let_randname (self, wds=None) :
        if wds is None :
            wds = self.env["english"]
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
    def _let_randint (self, a, b, len=0, unique=False) :
        if len :
            if unique :
                values = random.sample(range(a, b+1), len)
            else :
                values = [random.randint(a, b) for i in range(len)]
            return "{" + ", ".join(str(v) for v in values) + "}"
        else :
            return random.randint(a, b)
    def _let_choice (self, *args) :
        return random.choice(args)
    def _let_shufflestring (self, val) :
        l = list(str(val))
        random.shuffle(l)
        return String("".join(l))
    def _let_islet (self, name) :
        return name in self.cppenv

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
