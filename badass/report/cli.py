from pathlib import Path
from . import Report

def add_arguments (sub) :
    sub.add_argument("-b", "--base", type=str, required=True,
                     help="base directory to be searched for projects")
    sub.add_argument("-p", "--path", type=str, required=True,
                     help="target path of report file")
    sub.add_argument("-e", "--exercise", type=str, required=True, action="append",
                     help="exercise to be included")
    sub.add_argument("students", default=[], nargs="+",
                     help="students identifiers")

def main (args) :
    "build report from submitted projects"
    rep = Report(Path(args.base), args.exercise, set(args.students))
    rep.save(Path(args.path))
