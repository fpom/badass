import argparse, sys

def add_arguments (sub) :
    excl = sub.add_mutually_exclusive_group(required=True)
    #
    excl.add_argument("-f", "--form", metavar="YAML",
                       type=argparse.FileType(mode="r", encoding="utf-8"),
                       help="generate form from YAML")
    group = sub.add_argument_group("form generation options")
    group.add_argument("-o", "--output", metavar="PATH",
                       type=argparse.FileType(mode="w", encoding="utf-8"),
                       default=sys.stdout,
                       help="output to PATH (default: stdout)")
    #
    excl.add_argument("-p", "--passwd", type=str, metavar="CSV",
                      help="password CSV database")
    group = sub.add_argument_group("passwords management options")
    group.add_argument("-u", "--user", default=[], action="append", type=str,
                       help="(re)generate password for selected user (default: all)")
    group.add_argument("-r", "--read", default=False, action="store_true",
                       help="read passwords interactively instead of generating them")
    group.add_argument("-d", "--default", default=None, action="store", type=str,
                       help="password to be used (dangerous)")
    group.add_argument("-l", "--log", default=sys.stdout,
                       type=argparse.FileType(mode="w", encoding="utf-8"),
                       help="log changed password to LOG (default: stdout)")
    #
    excl.add_argument("-s", "--serve", default=False, action="store_true",
                       help="start server")

def main (args) :
    "www server and utilities"
    print("www", args)
