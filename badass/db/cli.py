import argparse, sys, collections, ast, csv

from functools import reduce
from operator import and_

from parsedatetime import Calendar

from . import connect

def add_arguments (sub) :
    sub.add_argument("-p", "--path", type=str, default=".",
                     help="PATH where the database is stored")
    sub.add_argument("-a", "--all", default=False, action="store_true",
                     help="print all fields")
    sub.add_argument("-m", "--matched", default=False, action="store_true",
                     help="print matched fields")
    sub.add_argument("-d", "--delete", default=False, action="store_true",
                     help="delete matched records instead of printing them")
    sub.add_argument("-l", "--list", default=False, action="store_true",
                     help="list fields in the database")
    sub.add_argument("-c", "--csv", metavar="PATH",
                     type=argparse.FileType("w"), default=None,
                     help="dump matched records as CSV")
    sub.add_argument("field", metavar="FIELD[=VALUE]", type=str, nargs="*",
                     help="fields to be printed (FIELD) or searched for (FIELD=VALUE)")

class DALAL (object) :
    def __init__ (self, path) :
        self.db, _, _, _ = connect(path)
        self.tables = {t : {f : getattr(getattr(getattr(self.db, t), f), "type")
                            for f in getattr(self.db, t).fields}
                       for t in self.db.tables}
        self.fields = collections.defaultdict(list)
        for table, fields in self.tables.items() :
            for f in fields :
                self.fields[f].append(table)
    def _search (self, s, among) :
        if s in among :
            return s
        candidates = [a for a in among if a.startswith(s)]
        if not candidates :
            raise ValueError(f"not match for '{s}'")
        elif len(candidates) > 1 :
            raise ValueError(f"more than one match for '{s}'")
        return candidates[0]
    _normalize = str.maketrans(",;:/ |_", ".......")
    def _split (self, s) :
        return str(s).translate(self._normalize).split(".")
    def __getitem__ (self, name) :
        try :
            table, field = self._split(name)
        except :
            field = name
            table = self.fields.get(self._search(name, self.fields), None)
        if table is None :
            raise ValueError(f"no match for '{name}'")
        elif isinstance(table, list) :
            if len(table) > 1 :
                raise ValueError(f"more than one match for '{name}'")
            table = table[0]
        table = self._search(table, self.tables)
        field = self._search(field, self.tables[table])
        return table, field
    def get (self, name) :
        table, field = self[name]
        return getattr(getattr(self.db, table), field)
    def __call__ (self, **match) :
        if not(match) :
            return self.db()
        else :
            return self.db(reduce(and_, (self.get(m) == v for m, v in match.items())))
    def query (self, *show, **match) :
        rows = self(**match).select(*(self.get(f) for f in show))
        rows.compact = False
        for row in rows :
            yield row.as_dict()
    def delete (self, **match) :
        try :
            self(**match).delete()
        except :
            self.db.rollback()
            raise
        else :
            self.db.commit()
    def cast (self, table, field, value) :
        kind = self.tables[table][field]
        if kind.startswith("reference ") :
            if value.endswith(".id") :
                return self.get(value)
            else :
                return self._cast_id(value)
        elif kind.startswith("list:") :
            return [self._cast(v, kind[5:]) for v in self._split(value)]
        else :
            return self._cast(value, kind)
    def _cast (self, value, kind) :
        return getattr(self, f"_cast_{kind}", self._cast_string)(value)
    def _cast_string (self, value) :
        return str(value)
    def _cast_id (self, value) :
        return ast.literal_eval(value)
    def _cast_boolean (self, value) :
        return ast.literal_eval(value)
    _cal = Calendar()
    def _cast_datetime (self, value) :
        dt, success = self._cal.parseDT(value)
        if not success :
            raise ValueError(f"could not parse date '{value}'")
        return dt

def _main (args) :
    dal = DALAL(args.path)
    if args.list :
        for table, fields in dal.tables.items() :
            print(table)
            for field, type_ in fields.items() :
                print(f" .{field} ({type_})")
        return
    show = set()
    match = {}
    tables = set()
    for a in args.field :
        try :
            f, v = a.split("=", 1)
        except :
            f, v = a, None
        if v is None :
            table, field = dal[f]
            show.add(f"{table}.{field}")
            tables.add(table)
        else :
            table, field = dal[f]
            match[f"{table}.{field}"] = dal.cast(table, field, v)
            tables.add(table)
    if args.delete :
        if show :
            raise ValueError("cannot print and delete records")
        try :
            dal.delete(**match)
        except RuntimeError as err :
            raise ValueError(str(err))
        return
    show.update(f"{t}.id" for t in tables)
    if args.matched :
        show.update(match)
    if args.all :
        show.update(f"{t}.{f}" for t in tables for f in dal.tables[t])
    if args.csv is not None :
        rows = list(dal.query(*show, **match))
        cols = [f"{t}.id" for t in rows[0]]
        cols.extend(f"{t}.{f}" for t in rows[0] for f in rows[0][t] if f != "id")
        writer = csv.DictWriter(args.csv, cols)
        writer.writeheader()
        for row in rows :
            writer.writerow({f"{t}.{f}" : v for t in row for f, v in row[t].items()})
    else :
        from colorama import Style as S, Fore as F
        for row in dal.query(*show, **match) :
            print(" & ".join(f"{S.BRIGHT}{F.BLUE}{table}"
                             f"{F.RESET}.{F.RED}#{row[table]['id']}{S.RESET_ALL}"
                             for table in row))
            for table, fields in row.items() :
                for fname, value in fields.items() :
                    if fname == "id" :
                        continue
                    print(f"  {F.BLUE}{table}{F.RESET}.{F.GREEN}{fname}{F.RESET}"
                          f":{S.RESET_ALL} {value}")

def main (args) :
    "query the database"
    try :
        _main(args)
    except ValueError as err :
        print(f"error: {err}")
        sys.exit(1)
