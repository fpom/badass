import argparse

from . import dump

def add_arguments (sub) :
    sub.add_argument("-p", "--parser", default=None,
                     help="which parser to use")
    sub.add_argument("path", type=str,
                     help="source file to be parsed and dumped")


def main (args) :
    "dump AST from source file"
    dump(args.path, args.parser, args.lang)
