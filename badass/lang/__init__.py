import importlib, pathlib, tempfile, os

class BaseLanguage (object) :
    def __init__ (self, test_dir) :
        self.test_dir = test_dir
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir=self.test_dir))
    def __getitem__ (self, path) :
        return path.relative_to(self.test_dir)
    def _mkdtemp (self, **args) :
        args["dir"] = self.tmp
        return pathlib.Path(tempfile.mkdtemp(**args))
    def _mkstemp (self, **args) :
        args["dir"] = self.tmp
        fd, path = tempfile.mkstemp(**args)
        os.close(fd)
        return pathlib.Path(path)
    def _mktmp (self, head, *ext) :
        if not ext :
            ext = (".out", ".err", ".ret")
        names = [self._mkstemp(prefix=f"{head}-", suffix=f"{e}") for e in ext]
        if len(names) == 1 :
            return names[0]
        else :
            return tuple(names)

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
