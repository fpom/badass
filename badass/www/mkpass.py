import secrets, hashlib
from random import SystemRandom
from .wordlist import words, syllables

random = SystemRandom()

nonalpha = "".join(sorted(set("0123456789-+/*%,;.:!?$&#|@~{}()[]_<>")))

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
            return attempt

def salthash (s, p) :
    salted = (s + p).encode("utf-8")
    return hashlib.sha512(salted).hexdigest()
