from pathlib import Path
from ..lang import load as load_lang

def dump (path, parser, lang) :
    path = Path(path)
    mod = load_lang(lang)
    src = mod.Source(path.parent,  [path])
    if not parser :
        parser = next(iter(src.ast[path.name]))
    mod.print_ast(src.ast[path.name][parser], parser)
