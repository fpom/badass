version = "0.8"

import os, io
import chardet

from functools import wraps
from tempfile import mkstemp, mkdtemp
from json import JSONEncoder as _JSONEncoder
from pathlib import Path
from collections import deque

from colorama import Fore as F

markdown = None

class LabelledTree (object) :
    def __init__ (self, label, children=[]) :
        self.label = str(label)
        self.children = list(children)
    def _print (self, out, prefix=None, last=True) :
        if prefix is None :
            out.write(f"{self.label}\n")
        elif last :
            out.write(f"{prefix}{F.WHITE}└─{F.RESET} {self.label}\n")
        else :
            out.write(f"{prefix}{F.WHITE}├─{F.RESET} {self.label}\n")
        for child in self.children :
            if prefix is None :
                child._print(out, "", child is self.children[-1])
            elif last :
                child._print(out, prefix + "   ", child is self.children[-1])
            else :
                child._print(out, prefix + f"{F.WHITE}│{F.RESET}  ", child is self.children[-1])
    def __str__ (self) :
        out = io.StringIO()
        self._print(out)
        return out.getvalue().rstrip()

class tree (dict) :
    def __getattr__ (self, key) :
        cls = self.__class__
        val = self.get(key, None)
        if isinstance(val, dict) and not isinstance(val, cls) :
            val = self[key] = tree(val)
        elif isinstance(val, list) :
            val = self[key] = [tree(v) if isinstance(v, dict) and not isinstance(v, cls)
                               else v for v in val]
        return val
    def __setattr__ (self, key, val) :
        if isinstance(val, dict) :
            val = self.__class__(val)
        self[key] = val

cwd = Path().absolute()

def new_path (type="file", **args) :
    if type == "file" :
        fd, path = mkstemp(**args)
        os.close(fd)
    elif type == "dir" :
        path = mkdtemp(**args)
    else :
        raise ValueError(f"unsupported path type {type!r}")
    return Path(path).absolute().relative_to(cwd)

encoding = tree(encoding="utf-8",
                errors="replace")

class JSONEncoder (_JSONEncoder) :
    def default (self, obj) :
        handler = getattr(obj, "__json__", None)
        if handler is None :
            return super().default(obj)
        else :
            return handler()

def cached_property (method) :
     @wraps(method)
     def wrapper (self) :
         name = method.__name__
         if not hasattr(self, "__cache") :
             self.__cache = {}
         if name not in self.__cache :
             self.__cache[name] = method(self)
         return self.__cache[name]
     @wraps(method)
     def delete (self) :
         self.__cache.pop(method.__name__, None)
     return property(wrapper, None, delete, method.__doc__)

def recode (path) :
    with open(path, "rb") as inf :
        raw = inf.read()
    try :
        enc = chardet.detect(raw)
        src = raw.decode(enc["encoding"], errors="replace")
    except :
        return
    with open(path, "w", **encoding) as out :
        out.write(src)
    return src

def md (text, inline=True) :
    # only load if necessary to speedup prog startup
    global markdown
    from markdown import markdown
    #
    try :
        html = markdown(str(text))
        if inline :
            html = html.replace("<p>", "").replace("</p>", "")
        return html.replace("§", "&nbsp;")
    except :
        return text.replace("§", " ")

_esc = {c : f"\\{c}" for c in r"\`*_{}[]()#+-.!"}

def mdesc (text) :
    return str(text).translate(_esc)

def chmod_r (path) :
    q = deque([Path(path)])
    while q :
        sub = q.popleft()
        if sub.is_dir() :
            sub.chmod(sub.stat().st_mode | 0o750)
            q.extend(sub.iterdir())
        else :
            sub.chmod(sub.stat().st_mode | 0o640)
