LANGS = {"java" : "https://github.com/tree-sitter/tree-sitter-java.git",
         "c" : "https://github.com/tree-sitter/tree-sitter-c.git"}
LIB = "tslib.so"

##
##
##

from os import chdir
from pathlib import Path
from subprocess import check_output, STDOUT
from tree_sitter import Language

target = Path(__file__).parent.absolute() / "badass/lang" / LIB
build = Path("build")
build.mkdir(exist_ok=True, parents=True)
chdir(build)

repos = []
for name, repo in LANGS.items() :
    local = Path(repo).stem
    if not Path(local).exists() :
        print("cloning", repo)
        check_output(["git", "clone", repo, local], stderr=STDOUT)
    repos.append(local)
print("building", target)
if target.exists() :
    target.unlink()
assert Language.build_library(str(target), repos)

target_py = target.parent / "_tslib.py"
print("writing", target_py)
with target_py.open("w") as out :
    out.write(f"LANGS = {list(LANGS)!r}\n")
