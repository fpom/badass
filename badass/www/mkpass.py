import csv, pathlib, sys, getpass, secrets, hashlib
from random import SystemRandom
from .wordlist import words, syllables

random = SystemRandom()

nonalpha = "".join(sorted(set("0123456789-+/*=%,;.:!?$&#|@~{}()[]_<>")))

def pwgen (length=2) :
    while True :
        pw = []
        for s in random.sample(syllables, length) :
            if random.randint(0, 1) :
                s = s.capitalize()
            if random.randint(0, 1) :
                s = s.swapcase()
            pw.append(s)
        pw.extend(random.sample(nonalpha, random.randint(1, length)))
        random.shuffle(pw)
        attempt = "".join(pw)
        word = "".join(c for c in attempt if c not in nonalpha).lower()
        if word not in words :
            yield attempt

def salt () :
    while True :
        yield secrets.token_hex()

SALT = secrets.token_hex()

def salthash (s, p) :
    salted = (s + p).encode("utf-8")
    return hashlib.sha512(salted).hexdigest()

def mkpass (path, users=None, add=None, ask=False, default=None, log=sys.stdout) :
    if add :
        users = []
        with open(path, encoding="utf-8") as infile :
            old_fields = infile.readline().strip().split(",")
        with open(add, encoding="utf-8") as infile :
            add_fields = infile.readline().strip().split(",")
            missing = (set(old_fields) - {"password", "salt"}) - set(add_fields)
            if missing :
                raise ValueError(f"missing columns: {','.join(repr(s) for s in missing)}")
            add_key = add_fields[0]
            add_db = csv.DictReader(infile, add_fields)
            with open(path, "a", encoding="utf-8") as outfile :
                out = csv.DictWriter(outfile, old_fields,
                                     restval="", extrasaction="ignore")
                for row in add_db :
                    users.append(row[add_key])
                    out.writerow(row)
    lines = []
    pwd, slt = pwgen(), salt()
    with open(path, encoding="utf-8") as infile :
        fields = infile.readline().strip().split(",")
        salted = "salt" in fields
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
                if salted :
                    row["salt"] = next(slt)
                    row["password"] = salthash(row["salt"], password)
                else :
                    row["password"] = password
                lines.append(row)
                log.write(f"{row[key]} {password}\n")
            else :
                lines.append(row)
    pathlib.Path(path).rename(path + ".bak")
    with open(path, "w", encoding="utf-8") as outfile :
        db = csv.DictWriter(outfile, fields)
        db.writeheader()
        for row in lines :
            db.writerow(row)
