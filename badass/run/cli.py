import argparse

def add_arguments (sub) :
    sub.add_argument("-r", "--ressources", type=str, default=None, metavar="DIR",
                     help="path to resources")
    sub.add_argument("script", type=argparse.FileType("r", encoding="utf-8"),
                     help="path to script")
    sub.add_argument("project", type=str,
                     help="path to project")

def main (args) :
    "run assessment script"
    print("run", args)
