import sys
from pathlib import Path
from . import Report

def add_arguments (sub) :
    sub.add_argument("-o", "--output", metavar="PATH", type=str, required=True,
                     help="target path of report file")
    mutex = sub.add_mutually_exclusive_group(required=True)
    mutex.add_argument("-c", "--csv", metavar="PATH", type=str, default=None,
                       help="fetch info from CSV in file PATH")
    mutex.add_argument("-d", "--database", metavar="PATH", type=str,
                       help="fetch info from DB in directory PATH")
    sub.add_argument("-g", "--groups", default=[], nargs="+",
                     help="groups to be included into the report")
    sub.add_argument("-e", "--exos", default=[], nargs="+",
                     help="COURSE/EXERCISE to be included into the report")

def main (args) :
    "build report from submitted projects"
    if args.database :
        rep = Report.from_db(args.database, args.groups, args.exos)
    elif args.csv :
        rep = Report.from_csv(args.csv, args.groups, args.exos)
    else :
        print("error: use either --database or --csv",
              file=sys.stderr)
        sys.exit(2)
    rep.save(Path(args.output))
