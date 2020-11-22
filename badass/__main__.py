import argparse, setuptools, os.path, importlib, sys
import badass

def main (argv=None) :
    parser = argparse.ArgumentParser("badass",
                                     description="(not so) bad assessments")
    parser.add_argument("-v", "--version",
                        action="version",
                        version=badass.version)
    cmd = parser.add_subparsers(dest="command",
                                required=True,
                                title="available commands")
    handlers = {}
    for package in setuptools.find_packages(os.path.dirname(__file__)) :
        try :
            mod = importlib.import_module(f".{package}.cli", "badass")
            assert callable(mod.main)
            assert callable(mod.add_arguments)
        except :
            continue
        sub = cmd.add_parser(package, help=mod.main.__doc__)
        mod.add_arguments(sub)
        handlers[package] = mod.main
    args = parser.parse_args(argv)
    sys.exit(handlers[args.command](args))

if __name__ == "__main__" :
    main()
