import shlex, re
from ... import tree

_err = re.compile(r"^Error\s+\#(\d+):\s+(.*)$")
_sum = re.compile(r"^\s+(\d+)\s+unique,\s+(\d+)\s+total,?\s+(.*)$")
_ptr = re.compile(r"0x[0-9A-F]+-0x[0-9A-F]+\s*", re.I)
_key = re.compile(r"^([A-Z\s]+)")
_frm = re.compile(fr"^\#\s*\d+\s+(\S+)\s+\[([^:]+):(\d+)\]")

def parse (path) :
    res = tree(errors=tree())
    with open(path) as log :
        for line in log :
            if line.startswith("Dr. Memory version") :
                res.version = line.split()[3]
            elif line.startswith("Dr. Memory results for pid") :
                parts = shlex.split(line)
                pid = res.pid = int(parts[5].rstrip(":"))
                res.cmd = parts[-1]
                try :
                    with open(path.parent / f"global.{pid}.log") as pidlog :
                        for l in pidlog :
                            if l.startswith(f"process={pid},") :
                                res.parent = int(l.strip().rsplit("=")[-1])
                                break
                except :
                    pass
            elif line.strip() == "DUPLICATE ERROR COUNTS:" :
                for line in log :
                    if line.strip().startswith("Error #") :
                        parts = line.split()
                        res.errors[int(parts[2].rstrip(":"))].count = int(parts[-1])
                    else :
                        break
            elif line.strip() == "ERRORS FOUND:" :
                summary = res.summary = []
                for line in log :
                    match = _sum.match(line)
                    if not match :
                        return res
                    summary.append((int(match.group(1)),
                                    int(match.group(2)),
                                    match.group(3).strip()))
            else :
                match = _err.match(line)
                if match :
                    num = int(match.group(1))
                    err = res.errors[num] = tree()
                    desc = err.description = _ptr.sub("", match.group(2).strip())
                    match = _key.match(desc)
                    if match :
                        err.name = match.group(1).strip()
                    err.stack = []
                    for line in log :
                        match = _frm.match(line)
                        if not match :
                            break
                        err.stack.append(tree(function = match.group(1),
                                              path = match.group(2),
                                              line = int(match.group(3))))
    return res
