import shlex, re

_err = re.compile(r"^Error \#(\d+):\s+(.*)$")
_sum = re.compile(r"^\s+(\d+)\s+unique,\s+(\d+)\s+total,?\s+(.*)$")
_ptr = re.compile(r"0x[0-9A-F]+-0x[0-9A-F]+\s*", re.I)
_key = re.compile(r"^([A-Z\s]+)")

def parse (path, source, cwd) :
    _frm = re.compile(fr"^\#\s*0\s+(\S+)\s+\[{cwd.name}/([^:]+):(\d+)\]")
    res = {"errors": {}}
    with open(path) as log :
        for line in log :
            if line.startswith("Dr. Memory version") :
                res["version"] = line.split()[3]
            elif line.startswith("Dr. Memory results for pid") :
                parts = shlex.split(line)
                pid = res["pid"] = int(parts[5].rstrip(":"))
                res["cmd"] = parts[-1]
                with open(path.parent / f"global.{pid}.log") as pidlog :
                    for l in pidlog :
                        if l.startswith(f"process={pid},") :
                            res["parent"] = int(l.strip().rsplit("=")[-1])
                            break
            elif line.strip() == "DUPLICATE ERROR COUNTS:" :
                for line in log :
                    if line.strip().startswith("Error #") :
                        parts = line.split()
                        res["errors"][int(parts[2].rstrip(":"))]["count"] = int(parts[-1])
                    else :
                        break
            elif line.strip() == "ERRORS FOUND:" :
                summary = res["summary"] = []
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
                    err = res["errors"][int(match.group(1))] = {}
                    desc = err["description"] = _ptr.sub("", match.group(2).strip())
                    match = _key.match(desc)
                    if match :
                        err["name"] = match.group(1).strip()
                    for line in log :
                        match = _frm.match(line)
                        if not match :
                            break
                        src = match.group(2)
                        if src in source :
                            err["function"] = match.group(1)
                            err["path"] = match.group(2)
                            err["line"] = int(match.group(3))
                            break
    return res
