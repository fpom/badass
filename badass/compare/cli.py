import argparse

def add_arguments (sub) :
    sub.add_argument("-g", "--glob", metavar="GLOB", default=[], action="append",
                     help="files to include in comparison")
    sub.add_argument("--csv", type=argparse.FileType("w", encoding="utf-8"),
                     help="save distance matrix to CSV")
    sub.add_argument("--heatmap", metavar="PATH", type=str, default=None,
                     help="draw a clustered heatmap in PATH")
    sub.add_argument("--hmopt", default=[], action="append", type=str,
                     help="additional options for heatmap")
    sub.add_argument("--maxsize", metavar="COUNT", type=int, default=0,
                     help="split heatmap into clusters of at most COUNT projects")
    sub.add_argument("--absolute", default=False, action="store_true",
                     help="draw heatmap with absolute colors")
    sub.add_argument("--load", default=None, action="store", type=str, metavar="CSV",
                     help="load distance matrix from CSV instead of computing it")
    sub.add_argument("project", default=[], type=str, nargs="*",
                     help="project base dir (or single file)")

def main (args) :
    "compare projects"
    print("compare", args)
