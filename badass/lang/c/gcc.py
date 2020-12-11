import re, collections

from ... import tree

_fun = re.compile(r"^.+\.c?:\s*In\s+(.+?)\s+‘(.+)’:$")
_msg = re.compile(r"^(.+\.c?):(\d+):(\d+):\s*(warning|error):\s*(.+?)\s*(\[-.+\])?$")
_src = re.compile(r"^\s+\d*\s+\|.*$")

class GCCout (object) :
    def __init__ (self, ignore=[]) :
        self.ignore = set(ignore)
        self.messages = []
        self.count = collections.defaultdict(int)
    def add (self, message) :
        ign = message.ignored = message.mesg in self.ignore
        self.count[f"{'ignored_' if ign else ''}{message.kind}"] += 1
        if message.flag :
            message.flag = message.flag.strip("[]")
        self.messages.append(message)
    def errors (self, ignored=False) :
        for message in self.messages :
            if message.kind == "error" :
                if message.ignored and not ignored :
                    continue
                yield message
    def warnings (self, ignored=False) :
        for message in self.messages :
            if message.kind == "warning" :
                if message.ignored and not ignored :
                    continue
                yield message
    def error_count (self, ignored=False) :
        count = self.count["error"]
        if ignored :
            count += self.count["ignored_error"]
        return count
    def warning_count (self, ignored=False) :
        count = self.count["warning"]
        if ignored :
            count += self.count["ignored_warning"]
        return count
    def parse (self, log) :
        head = []
        last = unit = name = None
        for line in log.splitlines() :
            match = _fun.match(line)
            if match is not None :
                unit = match.group(1)
                name = match.group(2)
                head.append(line)
                continue
            match = _msg.match(line)
            if match is not None :
                if last is not None :
                    self.add(last)
                last = tree(path = match.group(1),
                            name = name,
                            unit = unit,
                            line = int(match.group(2)),
                            col  = int(match.group(3)),
                            kind = match.group(4),
                            mesg = match.group(5),
                            flag = match.group(6),
                            text = head + [line])
                head = []
                unit = name = None
                continue
            match = _src.match(line)
            if match is not None :
                last.text.append(line)
                continue
            head.append(line)
        if last is not None :
            self.add(last)
