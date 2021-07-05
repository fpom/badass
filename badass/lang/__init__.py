import importlib, pathlib

try :
    import sys, os
    assert os.isatty(sys.stdout.fileno())
    import colorama
    COL = {"key" : colorama.Fore.BLUE + colorama.Style.BRIGHT,
           "imp" : colorama.Fore.BLUE,
           "dim" : colorama.Fore.LIGHTBLACK_EX,
           "clr" : colorama.Style.RESET_ALL}
except :
    COL = {"key" : "",
           "imp" : "",
           "dim" : "",
           "clr" : ""}

class BaseLanguage (object) :
    SUFFIX = None
    def __init__ (self, test) :
        self.test = test
    def add_source (self, source, path) :
        raise NotImplementedError
    def del_source (self, name) :
        raise NotImplementedError
    def make_script (self) :
        raise NotImplementedError
    def report (self) :
        raise NotImplementedError
    def decl (self, signature) :
        raise NotImplementedError

class BaseASTPrinter (object) :
    IMPORTANT = {}
    GROUP = {}
    CHILDREN = {}
    FORMAT = {}
    IGNORE = {}
    def __init__ (self, tree, parser) :
        self.parser = parser
        self.important = self.IMPORTANT.get(parser, [])
        self.children = self.CHILDREN.get(parser, [])
        self.group = self.GROUP.get(parser, {})
        self.format = self.FORMAT.get(parser, {})
        self.ignore = (set(self.IGNORE.get(parser, []))
                       | set(self.IMPORTANT.get(parser, []))
                       | set(self.CHILDREN.get(parser, [])))
        self(tree)
    def __call__ (self, tree, indent="") :
        ignore = set(self.ignore)
        for k in self.important :
            if k in tree :
                print(f"{indent}{COL['key']}{k}{COL['clr']}"
                      f": {COL['imp']}{tree[k]}{COL['clr']}")
        for g, l in self.group.items() :
            try :
                line = l.format(**tree)
                print(f"{indent}{line}")
                ignore.update(g)
            except :
                pass
        for k, v in tree.items() :
            if k in self.ignore :
                continue
            elif not v :
                continue
            elif k in self.format :
                try :
                    print(f"{indent}{k}:", self.format[k].format(val=v))
                except :
                    print(f"{indent}{k}: {v}")
            elif isinstance(v, dict) :
                print(f"{indent}{k}:")
                self(v, indent + "  ")
            else :
                print(f"{indent}{k}: {v}")
        for c in self.children :
            for num, sub in enumerate(tree.get(c, [])) :
                print(f"{indent}{COL['dim']}{c}[{num}]:{COL['clr']}")
                self(sub, indent + "  ")

def load (lang) :
    name = lang.strip().lower()
    try :
        mod = importlib.import_module(f".lang.{name}", "badass")
        assert issubclass(mod.Language, BaseLanguage)
        return mod
    except :
        raise ValueError(f"langage {lang} not supported")

def supported () :
    for path in pathlib.Path(__file__).parent.iterdir() :
        try :
            mod = load(path.name)
            yield mod.NAMES, mod.DESCRIPTION
        except :
            pass
