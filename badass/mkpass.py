import secrets, hashlib, unicodedata
from random import SystemRandom
from .wordlist import words, syllables

random = SystemRandom()

nonalpha = "".join(sorted(set("0123456789-+/*%,;.:!?$&#|@~{}()[]_<>")))

def strong (p) :
    cats = {c if (c := unicodedata.category(s)).startswith("L") else c[0] for s in p}
    splt = set("".join(s.lower() if unicodedata.category(s).startswith("L") else " "
                        for s in p).split()) - {""}
    return (len(p) >= 8
            and p.lower() not in words
            and len(cats) > 2
            and not any(w in words for w in splt if len(w) > 3))

def pwgen (strenght=2) :
    while True :
        pw = []
        for s in random.sample(syllables, strenght) :
            if random.randint(0, 1) :
                s = s.capitalize()
            if random.randint(0, 1) :
                s = s.swapcase()
            pw.append(s)
        pw.extend(random.sample(nonalpha, 1 + random.randint(1, strenght)))
        random.shuffle(pw)
        attempt = "".join(pw)
        word = "".join(c for c in attempt if c not in nonalpha).lower()
        if word not in words and strong(attempt) :
            return attempt

def salthash (s, p) :
    salted = (s + p).encode("utf-8")
    return hashlib.sha512(salted).hexdigest()

