LANGS = {"java" : "https://github.com/tree-sitter/tree-sitter-java.git",
         "c" : "https://github.com/tree-sitter/tree-sitter-c.git"}
LIB = "tslib.so"

##
##
##

from os import chdir
from pathlib import Path
from subprocess import check_output, STDOUT
from tempfile import TemporaryDirectory
from tree_sitter import Language

target = Path(__file__).parent.absolute() / "badass/lang" / LIB

with TemporaryDirectory() as tmpdir :
    chdir(tmpdir)
    repos = []
    for name, repo in LANGS.items() :
        print("cloning", repo)
        local = Path(repo).stem
        check_output(["git", "clone", repo, local], stderr=STDOUT)
        repos.append(local)
    print("building", target)
    if target.exists() :
        target.unlink()
    assert Language.build_library(str(target), repos)
