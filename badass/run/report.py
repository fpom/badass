import io, json, csv

from zipfile import ZipFile, ZIP_LZMA, ZIP_STORED

from .. import tree, md

class Tag (object) :
    def __init__ (self, html, name) :
        self._html = html
        self._name = name.lower()
        self._attr = {}
    def __call__ (self, **attr) :
        self._attr.update({k.lower() : v for k, v in attr.items()})
        return self
    def __enter__ (self) :
        attr = []
        for key, val in self._attr.items() :
            if val is None :
                attr.append(key)
            else :
                attr.append(f'{key}="{val}"')
        self._html.write(f"<{self._name}{' ' if attr else ''}{' '.join(attr)}>")
        return self
    def __exit__ (self, exc_type, exc_val, exc_tb) :
        self._html.write(f"</{self._name}>")

class HTML (object) :
    def __init__ (self, out) :
        self._out = out
    def __getattr__ (self, name) :
        return Tag(self, name)
    def write (self, text) :
        self._out.write(text)
    def getvalue (self) :
        return self._out.getvalue()

class Report (object) :
    def __init__ (self, project, tests) :
        self.project_dir = project
        self.tests = tests
        self._csv = io.StringIO()
        self.csv = csv.DictWriter(self._csv, ["test", "status", "auto", "text", "details"])
        self.csv.writeheader()
        self.json = []
    def save (self) :
        with (self.project_dir / "report.zip").open("wb") as out :
            with ZipFile(out, "w", compression=ZIP_STORED) as zf :
                for path in self.tests :
                    html_path = path.with_suffix(".html").name
                    html_data = self.add_test(path, html_path)
                    zf.writestr(html_path, html_data,
                                compress_type=ZIP_LZMA, compresslevel=9)
                    zf.write(path, path.name)
                    path.unlink()
                zf.writestr("report.csv", self._csv.getvalue(),
                            compress_type=ZIP_LZMA, compresslevel=9)
                zf.writestr("report.json", json.dumps(self.json),
                            compress_type=ZIP_LZMA, compresslevel=9)
    def add_test (self, path, html_path) :
        html = io.StringIO()
        self.html = HTML(html)
        with ZipFile(path) as zf :
            with zf.open(f"test.json") as raw :
                test = tree(json.load(raw))
        row = {k : test.get(k, "") for k in self.csv.fieldnames}
        row["test"] = test["test"] = int(path.stem.split("-")[-1])
        self.csv.writerow(row)
        self.json.append(dict(status=test.status,
                              text=md(test.text),
                              path=path.name,
                              html=html_path))
        if test.details or test.checks :
            with self.html.div(CLASS="result-details") :
                self._add_checks(test)
        return self.html.getvalue()
    def _add_checks (self, test, nest_level=1) :
        if nest_level > 1 :
            self.html.write("<br>")
        if test.details :
            self.html.write(md(test.details))
        if test.checks :
            with self.html.ul :
                for num, chk in enumerate(test.checks) :
                    row = {k : chk.get(k, "") for k in self.csv.fieldnames}
                    row["test"] = chk["test"] = f"{test.test}.{num+1}"
                    self.csv.writerow(row)
                    with self.html.li(CLASS=f"result-{chk.status}") :
                        with self.html.span(CLASS="result-item-text") :
                            self.html.write(f"{md(chk.text)}")
                        self._add_checks(chk, nest_level+1)
