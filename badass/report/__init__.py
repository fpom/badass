from collections import namedtuple
from zipfile import ZipFile, ZIP_STORED, ZIP_LZMA
from pathlib import Path
from io import StringIO
from csv import DictReader, DictWriter
from os.path import commonprefix

from .. import encoding

submission = namedtuple("submission", ["student", "exercise", "date", "path"])

_test = {"pass" : 0,
         "warn" : 1,
         "fail" : 2}

class Report (object) :
    def __init__ (self, base, students) :
        self.todo = []
        root = base.parent
        for path in self._walk(base, students) :
            short = path.relative_to(root)
            *exercise, student, day, time = short.parts
            date = f"{day} {time}"
            self.todo.append(submission(student, "/".join(exercise), date, path))
    def _walk (self, root, students=None) :
        for path in root.iterdir() :
            if path.is_file() and students is None :
                yield path
            elif path.is_dir() :
                if students is not None and path.name in students :
                    yield from path.glob("*/*")
                else :
                    yield from self._walk(path, students)
    def save (self, path) :
        with ZipFile(path, "w", compression=ZIP_STORED) as zf :
            zf.writestr("report.csv", self.csv(),
                        compress_type=ZIP_LZMA, compresslevel=9)
            for sub in self.todo :
                base = Path(sub.student) / sub.date.replace(" ", "@")
                for path in self._walk(sub.path) :
                    if path.suffix == ".zip" :
                        comp = {}
                    else :
                        comp = {"compress_type" : ZIP_LZMA,
                                "compresslevel" : 9}
                    zf.write(path, base / path.relative_to(sub.path), **comp)
    def csv (self) :
        headers = {(0, 1) : "student",
                   (0, 2) : "exercise",
                   (0, 3) : "date",
                   (0, 4) : "missing report"}
        csv_data = {}
        for sub in self.todo :
            try :
                path = sub.path / "report.zip"
                with ZipFile(path) as zf :
                    data = csv_data[sub.path] = zf.read("report.csv").decode(**encoding)
            except :
                continue
            data = StringIO(data)
            reader = DictReader(data)
            for row in reader :
                num = tuple(int(n) for n in str(row["test"]).split("."))
                txt = row["text"].lstrip("> ")
                if num not in headers :
                    headers[num] = txt
                elif headers[num] != txt :
                    headers[num] = commonprefix([txt, headers[num]])
        data = StringIO()
        out = DictWriter(data, [v for _, v in sorted(headers.items())])
        out.writeheader()
        for sub in self.todo :
            outrow = {"student" : sub.student,
                      "exercise" : sub.exercise,
                      "date" : sub.date}
            if sub.path not in csv_data :
                outrow["missing report"] = 1
                out.writerow(outrow)
                continue
            reader = DictReader(StringIO(csv_data[sub.path]))
            for row in reader :
                num = tuple(int(n) for n in str(row["test"]).split("."))
                outrow[headers[num]] = _test[row["status"]]
            out.writerow(outrow)
        return data.getvalue()
