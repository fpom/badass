import os, subprocess, re
from clang.cindex import Index, Config, CursorKind

if not getattr(Config, "library_file", None) :
    if "BADASS_LIBCLANG" in os.environ :
        Config.set_library_file(os.environ["BADASS_LIBCLANG"])
    else :
        try :
            ldconf = subprocess.run(["ldconfig", "-p"],
                                    encoding="utf-8", capture_output=True).stdout
        except :
            raise RuntimeError("could not load libclang")
        _libclang = re.compile(r"^libclang(?:-[0-9.]+)?\.so(?:\.[0-9]+)?\b.*?=>\s+(.*)$")
        for line in (l.strip() for l in ldconf.splitlines()) :
            match = _libclang.match(line)
            if match :
                Config.set_library_file(match.group(1))
                break
        else :
            raise RuntimeError("could not load libclang")

__all__ = [Index, CursorKind]
