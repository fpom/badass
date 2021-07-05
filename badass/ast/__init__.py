from pathlib import Path
from ..lang import load as load_lang

def dump (path, parser, lang) :
    mod = load_lang(lang)
    src = mod.Source(Path(path))
    key = next(iter(src.ast))
    if not parser :
        parser = next(iter(src.ast[key]))
    mod.ASTPrinter(src.ast[key][parser], parser)
