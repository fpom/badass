import argparse, pathlib, importlib, sys
import badass

from . import tree

class ListLangages (argparse.Action) :
    def __call__ (self, parser, namespace, values, option_string=None) :
        from badass.lang import supported
        print("Supported languages:")
        for names, description in supported() :
            if len(names) > 1 :
                alias = ", ".join(repr(n) for n in names[1:])
                print(f" - {names[0]!r}: {description} (alias: {alias})")
            else :
                print(f" - {names[0]!r}: {description}")
        parser.exit(0)

def main (argv=None) :
    parser = argparse.ArgumentParser("badass",
                                     description="(not so) bad assessments")
    parser.add_argument("-v", "--version",
                        action="version",
                        version=badass.version)
    parser.add_argument("-l", "--lang", default="C", type=str,
                        help="select programming language (default: 'C')")
    parser.add_argument("-L", "--list-lang", action=ListLangages, nargs=0,
                        help="list supported programming languages")
    cmd = parser.add_subparsers(dest="command",
                                required=True,
                                title="available commands")
    handlers = {}
    for path in pathlib.Path(__file__).parent.iterdir() :
        try :
            package = path.name
            mod = importlib.import_module(f".{package}.cli", "badass")
            assert callable(mod.main)
            assert callable(mod.add_arguments)
        except :
            continue
        sub = cmd.add_parser(package, help=mod.main.__doc__)
        mod.add_arguments(sub)
        handlers[package] = mod.main
    args = parser.parse_args(argv)
    args = tree((key, getattr(args, key)) for key in dir(args) if not key.startswith("_"))
    sys.exit(handlers[args.command](args))

if __name__ == "__main__" :
    main()
