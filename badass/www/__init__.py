from pathlib import Path
from shutil import copyfile
from secrets import token_bytes

from .. import encoding

def walk (path, root=None,
          collect={"yaml", "csv", "bad", "json", "cfg",
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

makefile_src = r"""all: static/index.js

serve: all
	badass www -s --no-pin

static/%.js: forms/%.yaml
	badass www --form $< --output $@
"""

def copy_static (target_dir, clobber=False) :
    # directories
    for child in ("data", "forms", "reports", "scripts", "static", "upload", "errors") :
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

def _input (name, default, check=lambda v: True, valid=None, read=input,
            convert=None, retype=False) :
    value = default
    while True :
        if value is not None :
            if check(value) :
                return value
            if valid :
                print(f"! invalid {name}, allowed values are:")
                for v in valid :
                    print(f"   - {v}" if not v.startswith("-") else f"      {v}")
            else :
                print(f"! invalid {name}")
        value = read(f"{name}: ")
        if convert is not None :
            value = convert(value)
        if retype :
            other = read(f"retype {name}: ")
            if convert is not None :
                other = convert(other)
            if value != other :
                print(f"! values do not match, please retry")
                value = None

def add_user (args) :
    from getpass import getpass
    from .db import connect
    from .mkpass import strong
    DB, CFG, USER, ROLES = connect(args.dbpath)
    fields = {"email" : _input("email", args.email),
              "firstname" : _input("first name", args.firstname),
              "lastname" : _input("last name", args.lastname),
              "studentid" : _input("student number", args.studentid),
              "group" : _input("group", args.group,
                               check=lambda g : not g or g.upper() in CFG.GROUPS,
                               valid=[f"{k}: {v}" for k, v in CFG.GROUPS.items()]),
              "roles" : _input("roles", args.roles,
                               check=lambda rrr : all(r in ROLES for r in rrr),
                               valid=list(ROLES),
                               convert=lambda v : v.strip().split()),
              "password" : _input("password", args.password,
                                  check=strong,
                                  valid=["not composed of existing words",
                                         "at least 8 characters long",
                                         "with 3+ kinds of characters among",
                                         "- uppercase letters",
                                         "- lowercase letters",
                                         "- digits",
                                         "- punctuations",
                                         "- other signs"],
                                  read=getpass,
                                  retype=True),
              "activated" : _input("activated", args.activated,
                                   check=lambda a : isinstance(a, bool),
                                   valid=["y[es]", "n[o]"],
                                   convert=lambda a : a.lower()[0] == "y"
                                   if a and a.lower()[0] in "yn" else a)}
    if not USER.add(**fields) :
        print("failed, this email may be already in use")
        sys.exit(1)
