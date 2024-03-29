import argparse, sys

def add_arguments (sub) :
    sub.add_argument("-g", "--glob", metavar="GLOB", default=[], action="append",
                     help="files to include in comparison")
    sub.add_argument("--csv", type=str, default=None,
                     help="save distance matrix to CSV")
    sub.add_argument("--heatmap", metavar="PATH", type=str, default=None,
                     help="draw a clustered heatmap in PATH")
    sub.add_argument("--hmopt", default=[], action="append", type=str,
                     help="additional options for heatmap")
    sub.add_argument("--maxsize", metavar="COUNT", type=int, default=0,
                     help="split heatmap into clusters of at most COUNT projects")
    sub.add_argument("--prune", metavar="VALUE", type=float, default=0,
                     help=("prune heatmap at 0 (no pruning) < VALUE < 1 (prune all),"
                           " or when no more than VALUE > 1 projects are left"))
    sub.add_argument("--absolute", default=False, action="store_true",
                     help="draw heatmap with absolute colors")
    sub.add_argument("--load", default=None, action="store", type=str, metavar="CSV",
                     help="load distance matrix from CSV instead of computing it")
    sub.add_argument("path", default=[], type=str, nargs="*",
                     help="path to one student project")

def main (args) :
    "compare projects"
    from . import Dist
    import pathlib, tqdm, ast
    projects = list(args.path)
    keys = [pathlib.Path(p).name for p in projects]
    if args.load :
        dist = Dist.read_csv(keys, args.load)
    else :
        dist = Dist(keys)
    todo = [(p, q) for i, p in enumerate(projects) for q in projects[i+1:]]
    for p, q in tqdm.tqdm(todo) :
        kp = pathlib.Path(p).name
        kq = pathlib.Path(q).name
        dist.add(kp, p, kq, q, *args.glob)
    if args.csv :
        dist.csv(args.csv)
    if args.heatmap :
        if (l := len(dist)) < 2 :
            sys.stderr.write(f"cannot plot heatmap for only {l} projects\n")
            sys.exit(0)
        options = {}
        for opt in args.hmopt :
            key, val = opt.split("=", 1)
            try :
                val = ast.literal_eval(val)
            except :
                pass
            options[key] = val
        dist.heatmap(args.heatmap,
                     max_size=args.maxsize,
                     prune=args.prune,
                     absolute=args.absolute,
                     **options)
