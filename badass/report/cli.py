from pathlib import Path
from . import Report

def add_arguments (sub) :
    sub.add_argument("-o", "--output", metavar="PATH", type=str, required=True,
                     help="target path of report file")
    sub.add_argument("-d", "--database", metavar="PATH", type=str, required=True,
                     help="PATH to database directory")
    sub.add_argument("-g", "--groups", default=[], nargs="+",
                     help="groups to be included into the report")
    sub.add_argument("-e", "--exos", default=[], nargs="+",
                     help="COURSE/EXERCISE to be included into the report")

def main (args) :
    "build report from submitted projects"
    rep = Report(args.database, args.groups, args.exos)
    rep.save(Path(args.output))
