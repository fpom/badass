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

makefile_src = r"""all: static/index.js static/teacher.js

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

def add_user (args) :
    from getpass import getpass
    from .db import connect
    db, cfg, User, Role = connect(args.dbpath)
    fields = {"email" : args.email or input("email: "),
              "firstname" : args.firstname or input("first name: "),
              "lastname" : args.lastname or input("last name: "),
              "studentid" : args.studentid or input("student number: ")}
    while True :
        group = fields["group"] = (args.group or input("group: " )).upper() or None
        if group is None or group in cfg.GROUPS :
            break
        args.groups = None
        print(f"invalid group: {group}")
        print("known groups are: ")
        for key, val in cfg.GROUPS.items() :
            print(f" - {key}: {val}")
    while True :
        roles = fields["roles"] = list(args.roles if args.roles is not None
                                       else input("role [role]...: " ).split())
        for role in roles :
            try :
                Role[role]
            except :
                print(f"invalid role: {role}")
                print("known roles are: ", ", ".join(str(r.value) for r in Role))
                break
        else :
            break
        args.roles = None
    while True :
        password = fields["password"] = args.password or getpass("password: ")
        if args.password is not None or password == getpass("retype password: ") :
            break
        print("passwords do not match, please retry")
    fields["activated"] = (args.activated if args.activated is not None
                           else input("activate [y/N]: ").lower().startswith("y"))
    if not User.add(**fields) :
        print("failed, this email may be already in use")
        sys.exit(1)
