from pathlib import Path
from shutil import copyfile
from secrets import token_bytes

from .. import encoding

def walk (path, root=None,
          collect={"yaml", "csv", "bad", "json",
                   "svg", "ico", "gif", "png",
                   "mp4",
                   "html", "css", "js", "map"}) :
    if root is None :
        root = path
    for child in path.iterdir() :
        if child.is_dir() :
            if child.name != "__pycache__" :
                yield from walk(child, root)
        elif child.is_file() and child.suffix.lstrip(".").lower() in collect :
            yield child.relative_to(root)

makefile_src = r"""all: static/index.js static/teacher.js

serve: all
	badass www -s --no-pin

static/%.js: forms/%.yaml
	badass www -f $< -o $@
"""

def copy_static (target_dir, clobber=False) :
    # directories
    for child in ("data", "forms", "permalink", "scripts", "static", "upload") :
        (target_dir / child).mkdir(exist_ok=True, parents=True)
    # resource files
    root = Path(__file__).parent
    for path in walk(root) :
        target = target_dir / path
        if target.exists() :
            if clobber :
                print("clobbering:", target)
                target.unlink()
            else :
                print("skipping:", target)
                continue
        target.parent.mkdir(exist_ok=True, parents=True)
        if path.parts[0] == "templates" :
            tpl = (root / path).read_text(**encoding)
            with target.open("w", **encoding) as out :
                out.write(tpl.replace("url_for('asset', kind='s', name=",
                                      "url_for('static', filename="))
        else :
            copyfile(root / path, target)
    # secret key
    secret_key = target_dir / "data" / "secret_key"
    if secret_key.exists() and not clobber :
        print("skipping:", secret_key)
    else :
        if clobber :
            print("clobbering:", secret_key)
        with secret_key.open("wb") as out :
            out.write(token_bytes())
    # Makefile
    makefile = target_dir / "Makefile"
    if makefile.exists() and not clobber :
        print("skipping:", makefile)
    else :
        if clobber :
            print("clobbering:", makefile)
        with makefile.open("w") as out :
            out.write(makefile_src)
