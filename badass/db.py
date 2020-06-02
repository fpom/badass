import sqlite3, pathlib, time

class DB (object) :
    def __init__ (self, path) :
        self.p = pathlib.Path(path).with_suffix("")
        self.p.mkdir(parents=True, exist_ok=True)
        self.d = sqlite3.connect(self.p.with_suffix(".db"))
        self.c = self.d.cursor()
        self.runs_cols = ("date", "project", "test",
                          "prep_ret", "prep_out", "prep_err",
                          "build_ret", "build_out", "build_err",
                          "run_ret", "run_out", "run_err", "run_sys", "run_ass")
        self._runs = ",".join("?" for c in self.runs_cols)
        self.checks_cols = ("date", "project", "test", "result")
        self._checks = ",".join("?" for c in self.checks_cols)
        self._create()
    def __del__ (self) :
        try :
            self.d.close()
        except :
            pass
    def close (self) :
        self.d.close()
    def _create (self) :
        todo = {"runs", "checks"}
        rows = self.c.execute("select name from sqlite_master WHERE type='table'")
        todo.difference_update(r[0] for r in rows.fetchall())
        for table in todo :
            cols = ",".join(getattr(self, f"{table}_cols"))
            self.c.execute(f"CREATE TABLE {table} ({cols})")
        if todo :
            self.d.commit()
    def _add (self, table, *cols) :
        _cols = getattr(self, f"{table}_cols")
        assert len(_cols) == len(cols)
        _patt = getattr(self, f"_{table}")
        try :
            self.c.execute(f"INSERT INTO {table} VALUES ({_patt})", cols)
            self.d.commit()
        except :
            self.d.rollback()
            raise
    def add_run (self, project, test, run) :
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        now_d, now_t = now.split()
        base_dir = pathlib.Path(self.p / now_d / "-".join(now_t.split(":")[:2]))
        base_dir.mkdir(parents=True, exist_ok=True)
        now, base_dir = self._now()
        cols = [now, project, test]
        for name in ["prep", "build", "run"] :
            for ext in ["ret", "out", "err", "sys", "ass"] :
                if name != "run" and ext in ("sys", "ass") :
                    continue
                key = f"{name}.{ext}"
                val = run[key]
                if isinstance(val, (int, float)) :
                    cols.append(val)
                elif isinstance(val, (list, tuple, dict)) :
                    cols.append(base_dir / key)
                    with open(cols[-1], "w") as f :
                        f.write(repr(val))
                elif isinstance(val, str) :
                    cols.append(base_dir / key)
                    with open(cols[-1], "w") as f :
                        f.write(val)
                elif callable(getattr(val, "write", None)) :
                    cols.append(base_dir / key)
                    with open(cols[-1], "w") as f :
                        val.write(f)
                else :
                    raise ValueError(f"cound not save {key} = {val!r}")
        self._add("runs", *cols)
    def add_check (self, project, test, result) :
        self._add("checks", time.strftime("%Y-%m-%d %H:%M:%S"),
                  project, test, str(result))
