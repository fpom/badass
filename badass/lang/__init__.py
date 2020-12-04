import importlib, pathlib

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
