import sys, tempfile

import pandas as pd

from collections import namedtuple
from zipfile import ZipFile, ZIP_STORED, ZIP_LZMA
from pathlib import Path
from io import StringIO
from csv import DictReader, DictWriter

from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import PatternFill, Alignment

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
        self.todo.sort()
        self.load_data()
        self.update_data()
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
            zf.writestr("report.xlsx", self.xlsx(),
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
    def load_data (self) :
        headers = {(0, 1) : "student",
                   (0, 2) : "exercise",
                   (0, 3) : "score",
                   (0, 4) : "total",
                   (0, 5) : "date",
                   (0, 6) : "missing report",
                   (sys.maxsize, 0) : "permalink"}
        csv_data = {}
        permalink = {}
        for sub in self.todo :
            try :
                path = sub.path / "report.zip"
                with ZipFile(path) as zf :
                    data = csv_data[sub.path] = zf.read("report.csv").decode(**encoding)
            except :
                continue
            permalink[sub.path] = (sub.path / "permalink").read_text(**encoding)
            data = StringIO(data)
            reader = DictReader(data)
            for row in reader :
                num = tuple(int(n) for n in str(row["test"]).split("."))
                if num not in headers and row["auto"] == "False" :
                    headers[num] = f"{row['test']}. {row['text']}"
        raw_data = StringIO()
        out = DictWriter(raw_data, [v for _, v in sorted(headers.items())])
        out.writeheader()
        for sub in self.todo :
            outrow = {"student" : sub.student,
                      "exercise" : sub.exercise,
                      "date" : sub.date,
                      "missing report" : 0}
            if sub.path not in csv_data :
                outrow["missing report"] = 1
            else :
                outrow["permalink"] = permalink[sub.path]
                reader = DictReader(StringIO(csv_data[sub.path]))
                for row in reader :
                    num = tuple(int(n) for n in str(row["test"]).split("."))
                    if num in headers :
                        outrow[headers[num]] = _test[row["status"]]
                score = count = 0
                for num in headers :
                    if len(num) == 1 :
                        score += outrow[headers[num]]
                        count += 1
                outrow["score"] = 2 * count - score
                outrow["total"] = 2 * count
            out.writerow(outrow)
        raw_data.seek(0)
        self.df = pd.read_csv(raw_data,
                              converters={"student" : str,
                                          "date" : pd.to_datetime,
                                          "missing report" : lambda c : bool(int(c))})
    def update_data (self) :
        df = self.df
        df.insert(df.columns.get_loc("score"), "mark", df["score"] / df["total"])
        df.insert(df.columns.get_loc("score"), "best", False)
        first = None
        last = (None, None)
        for idx, row in df.iterrows() :
            if (row["student"], row["exercise"]) != last :
                if first is not None :
                    best = df.loc[first:idx-1, "score"]
                    df.loc[first:idx-1, "best"] = best.eq(best.max())
                first = idx
                last = (row["student"], row["exercise"])
        best = df.loc[first:, "score"]
        df.loc[first:, "best"] = best.eq(best.max())
    def xlsx (self) :
        # convert dataframe into a workbook
        wb = self.wb = Workbook()
        ws = self.ws = wb.active
        for row in dataframe_to_rows(self.df, index=False, header=True):
            ws.append(row)
        # styling
        STYLES = {"student" : None,
                  "exercise" : None,
                  "mark" : self._xlsx_style_mark,
                  "best" : None,
                  "score" : None,
                  "total" : None,
                  "date" : None,
                  "missing report" : None,
                  "permalink" : self._xlsx_style_link}
        self.cname = cname = {cell.value : cell.column_letter for cell in ws[1]}
        for name, num in cname.items() :
            style = STYLES.get(name, self._xlsx_style_test)
            if isinstance(style, str) :
                for cell in ws[num] :
                    if cell.row > 1 :
                        cell.style = style
            elif callable(style) :
                for cell in ws[num] :
                    if cell.row > 1 :
                        style(cell)
        for cell in ws[cname["missing report"]] :
            if cell.value :
                for c in ws[cell.row] :
                    c.fill = PatternFill("solid", fgColor="AAAAAAAA")
        for cell in ws[cname["date"]] :
            if cell.row > 1 :
                cell.number_format = "MM-DD HH:MM"
        for cell in ws[1] :
            cell.style = "Note"
            if cell.value not in STYLES :
                cell.alignment = Alignment(textRotation=90)
        # resizing
        WIDTH = {"student" : 12,
                 "exercise" : 12,
                 "mark" : 8,
                 "best" : 8,
                 "score" : 0,
                 "total" : 0,
                 "date" : 12,
                 "missing report" : 0,
                 "permalink" : 10}
        for name, num in cname.items() :
            width = WIDTH.get(name, 3)
            if width == 0 :
                ws.column_dimensions[num].hidden = True
            else :
                ws.column_dimensions[num].width = width
        ws.row_dimensions[1].height = 200
        # add filter
        ws.auto_filter.ref = ws.dimensions
        # save workbook and return it
        with tempfile.NamedTemporaryFile(mode="w+b", suffix=".xlsx") as tmp :
            wb.save(tmp.name)
            tmp.seek(0)
            return tmp.read()
    def _xlsx_style_mark (self, cell) :
        best = self.ws[f"{self.cname['best']}{cell.row}"]
        if best.value :
            style = "Good"
        else :
            style = "Normal"
        for col in ("student", "exercise", "mark", "best", "date") :
            self.ws[f"{self.cname[col]}{cell.row}"].style = style
        if not pd.isna(cell.value) :
            cell.value = (f"={self.cname['score']}{cell.row}"
                          f"/{self.cname['total']}{cell.row}")
        cell.number_format = "0%"
        best.number_format = "BOOLEAN"
    def _xlsx_style_test (self, cell) :
        if cell.value == 0 :
            cell.style = "Good"
        elif cell.value == 1 :
            cell.style = "Neutral"
        else :
            cell.style = "Bad"
    def _xlsx_style_link (self, cell) :
        if isinstance(cell.value, str) :
            cell.hyperlink = cell.value
            cell.value = "see report"
        return "Hyperlink"
