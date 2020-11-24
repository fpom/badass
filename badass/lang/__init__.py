import importlib, pathlib

def load (lang) :
    name = lang.strip().lower()
    try :
        mod = importlib.import_module(f".lang.{name}", "badass")
        mod.NAMES
        mod.DESCRIPTION
        assert callable(mod.build)
        assert callable(mod.run)
        assert callable(mod.report)
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
