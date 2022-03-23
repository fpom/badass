from pathlib import Path
from collections import defaultdict
from ast import literal_eval
from datetime import timedelta
import pickle, re, fnmatch

from ._strace import straceParser

class STast (dict) :
    def __getattr__ (self, key) :
        try :
            return self[key]
        except KeyError :
            raise AttributeError(key)

def _const (text) :
    try :
        return literal_eval(text)
    except :
        return text

class Parser (object) :
    def __init__ (self) :
        self.p = straceParser()
    def __call__ (self, line) :
        return self.p.parse(line.strip(), semantics=self)
    def start (self, st) :
        """
        start =
            time:atom
            event:( syscall | signal | exit )
            $
            ;
        """
        return STast(st.event,
                     time=timedelta(seconds=st.time))
    def syscall (self, st) :
        """
        syscall =
            call:call
            "=" ret:( atom | "?" )
            info:/.*/
            ;
        """
        return STast(st.call,
                     kind="syscall",
                     ret=None if st.ret == "?" else st.ret,
                     info=st.info.strip() or None)
    def call (self, st) :
        """
        call =
            func:name
            "(" args:","%{ [ name "=" ] expr } ")"
            ;
        """
        return STast(kind="call",
                     name=st.func,
                     args=[STast(kind="arg", name=a[0], value=a[2])
                           if isinstance(a, list)
                           else STast(kind="arg", name=None, value=a)
                           for a in st.args if a != ","])
    def signal (self, st) :
        """
        signal =
            "---" sig:name info:struct "---"
            ;
        """
        return STast(kind="signal",
                     name=st.sig,
                     info=st.info)
    def exit (self, st) :
        """
        exit =
            "+++" "exited" "with" status:atom "+++"
            ;
        """
        return STast(kind="exit",
                     status=st.status)
    def atom (self, st) :
        """
        atom =
            /(?i)[+-]?[\w.]+/
            ;
        """
        return _const(st)
    def name (self, st) :
        """
        name =
            /\w+/
            ;
        """
        return str(st)
    def expr (self, st) :
        """
        expr =
            value:( t:string | a:array | s:struct | c:call | v:atom )
            [ "..." ]
            [ info:comment ]
            [ op:operator right:expr ]
            ;
        """
        if isinstance(st.value, STast) :
            left = STast(st.value,
                         info=st.info or None)
        else :
            left = STast(kind="expr",
                         value=st.value,
                         info=st.info or None)
        if st.op :
            return STast(kind="binexpr",
                         left=left,
                         op=st.op,
                         right=st.right)
        else :
            return left
    def comment (self, st) :
        """
        comment =
            ?"/\*(\*(?!/)|[^*])*\*/"
            ;
        """
        return st[2:-2].strip()
    def string (self, st) :
        """
        string =
            /(?i)\"[^\"]*\"/
            ;
        """
        return STast(kind="string",
                     value=_const(st))
    def array (self, st) :
        """
        array =
            "[" ","%{ expr } "]"
            ;
        """
        return STast(kind="array",
                     values=st[1][::2])
    def struct (self, st) :
        """
        struct =
            "{" fields:","%{ [ name "=" ] expr } "}"
            ;
        """
        return STast(kind="struct",
                     fields=[STast(kind="field", name=f[0], value=f[2])
                             if isinstance(f, list)
                             else STast(kind="field", name=None, value=f)
                             for f in st.fields if f != ","])
    def operator (self, st) :
        """
        operator =
            | "&&" | "||" | "==" | "!=" | "<=" | ">="
            | ?"[\^&|+*/<>%-]"
            ;
        """
        return str(st)

class STrace (object) :
    def __init__ (self, path) :
        self.path = Path(path)
        self.trace = {}
        parse = Parser()
        for log in self.path.glob("log.*") :
            pid = int(log.suffix.lstrip("."))
            self.trace[pid] = []
            for line in log.open() :
                try :
                    self.trace[pid].append(parse(line))
                except :
                    self.trace[pid].append(line)
        roots = set(self.trace)
        self.tree = defaultdict(set)
        for pid, match in self.match("clone") :
            child = match.ret
            self.tree[pid].add(child)
            roots.discard(child)
        assert len(roots) == 1, "cannot find root pid"
        self.root = roots.pop()
    def dump (self, path) :
        with open(path, "wb") as outfile :
            pickle.dump(self, outfile)
    @classmethod
    def load (cls, path) :
        with open(path, "rb") as infile :
            return pickle.load(infile)
    def match (self, calls, pid=None) :
        if isinstance(calls, str) :
            calls = [calls]
            first = True
        else :
            first = False
        if pid is None :
            for pid, trace in self.trace.items() :
                for match in self._match(trace, calls) :
                    yield pid, (match[0] if first else match)
        else :
            for match in self._match(self.trace[pid], calls) :
                yield pid, (match[0] if first else match)
    def _match (self, trace, calls) :
        head, *tail = calls
        if head.startswith("SIG") :
            found, sequel = self._match_sig(head, trace)
        elif head.startswith("EXIT") :
            found, sequel = self._match_exit(head, trace)
        else :
            found, sequel = self._match_call(head, trace)
        if found :
            if tail :
                for match in self._match(sequel, tail) :
                    yield [found] + match
            else :
                yield [found]
            yield from self._match(sequel, calls)
    def _match_sig (self, sig, trace) :
        for idx, evt in enumerate(trace) :
            if evt.kind == "signal" and evt.name == "sig" :
                return evt, trace[idx+1:]
        return None, None
    def _match_exit (self, spec, trace) :
        try :
            _, status = int(spec.split(None, 1))
        except :
            status = None
        for idx, evt in enumerate(trace) :
            if evt.kind == "exit" and status is not None and evt.status == status :
                return evt, trace[idx+1:]
        return None, None
    def _match_call (self, name, trace) :
        if name.startswith("/") and name.endswith("/") :
            def match (n) :
                return bool(re.match(f"^({name[1:-1]})$", n))
        else :
            names = name.split("|")
            def match (n) :
                return any(fnmatch.fnmatch(n, p) for p in names)
        for idx, evt in enumerate(trace) :
            if isinstance(evt, str) :
                if match(evt) :
                    return evt, trace[idx+1:]
            elif evt.kind == "syscall" and match(evt.name) :
                return evt, trace[idx+1:]
        return None, None
