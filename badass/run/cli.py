import argparse
from . import ScriptRunner

def add_arguments (sub) :
    sub.add_argument("script", type=argparse.FileType("r", encoding="utf-8"),
                     help="path to script")
    sub.add_argument("project", type=str,
                     help="path to project")

def main (args) :
    "run assessment script"
    ScriptRunner(args.project, args.script, args.lang).run()

