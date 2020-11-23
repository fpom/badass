import subprocess, csv, pathlib, sys, getpass
from app import salthash

def pwgen () :
    while True :
        out = subprocess.check_output(["pwgen"], encoding="utf-8").strip()
        for line in out.splitlines() :
            for p in line.split() :
                yield p

def salt (n=2) :
    for p in pwgen() :
        yield p[:n]

def mkpass (path, users=None, ask=False, default=None, log=sys.stdout) :
    lines = []
    pwd, slt = pwgen(), salt()
    with open(path, encoding="utf-8") as infile :
        fields = infile.readline().strip().split(",")
        key = fields[0]
        db = csv.DictReader(infile, fields)
        for row in db :
            if users is None or row[key] in users :
                if default :
                    password = default
                elif ask :
                    password = getpass.getpass(f"type password for {row[key]}: ")
                    if getpass.getpass(f"type password again: ") != password :
                        print("passwords do not match, skipping")
                        continue
                else :
                    password = next(pwd)
                row["salt"] = next(slt)
                row["password"] = salthash(row["salt"], password)
                lines.append(row)
                log.write(f"{row[key]} {password}\n")
    pathlib.Path(path).rename(path + ".bak")
    with open(path, "w", encoding="utf-8") as outfile :
        db = csv.DictWriter(outfile, fields)
        db.writeheader()
        for row in lines :
            db.writerow(row)

if __name__ == "__main__" :
    import argparse
    parser = argparse.ArgumentParser("mkpass")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--user", default=[], action="append", type=str,
                       help="user for which password must be regenerated")
    group.add_argument("-a", "--all", dest="user", action="store_const", const=None,
                       help="change password for all users")
    parser.add_argument("-r", "--read", default=False, action="store_true",
                        help="read passwords interactively instead of generating them")
    parser.add_argument("-d", "--default", default=None, action="store", type=str,
                        help="password to be used (dangerous)")
    parser.add_argument("-l", "--log", default=sys.stdout,
                        type=argparse.FileType(mode="w", encoding="utf-8"),
                        help="log changed password to LOG")
    parser.add_argument("db", type=str,
                        help="password CSV database")
    args = parser.parse_args()
    mkpass(args.db, args.user, args.read, args.default, args.log)
