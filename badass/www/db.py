import csv, secrets, configparser, ast

from pydal import DAL, Field
from sqlite3 import IntegrityError
from flask_login import UserMixin
from .mkpass import salthash

class cfgtree (dict) :
    def __init__ (self, *keys) :
        for k in keys :
            self[k] = self.__class__()
    def __getitem__ (self, key) :
        return super().__getitem__(str(key).upper())
    def __setitem__ (self, key, val) :
        return super().__setitem__(str(key).upper(), val)
    def __getattr__ (self, name) :
        return super().__getitem__(name.upper())
    def items (self, *sections) :
        keep = set(s.upper() for s in sections)
        for key, val in super().items() :
            if keep and key not in keep :
                continue
            if isinstance(val, cfgtree) :
                for subkey, subval in val.items() :
                    yield f"{key}_{subkey}", subval
            else :
                yield key, val

class BadassDB (object) :
    def __init__ (self, path) :
        # sqlite DB
        self.db = DAL(f"sqlite://badass.sqlite", folder=path)
        self.db.define_table("users",
                             Field("email", "string", unique=True),
                             Field("firstname", "string"),
                             Field("lastname", "string"),
                             Field("password", "string"),
                             Field("salt", "string"),
                             Field("group", "string"),
                             Field("roles", "list:string"),
                             Field("studentid", "string"),
                             Field("activated", "boolean"))
        self.db.define_table("submissions",
                             Field("user", "reference users"),
                             Field("date", "datetime"),
                             Field("exercise", "string"),
                             Field("path", "string"))
        self.db.define_table("results",
                             Field("user", "reference users"),
                             Field("date", "datetime"),
                             Field("submission", "reference submissions"),
                             Field("savedto", "string"),
                             Field("permalink", "string"))
        self.db.define_table("reports",
                             Field("user", "reference users"),
                             Field("date", "datetime"),
                             Field("groups", "list:string"),
                             Field("exercises", "list:string"),
                             Field("path", "string"))
        # groups
        self.groups = {}
        with open(f"{path}/groups.csv", encoding="utf-8") as infile :
            groups_db = csv.DictReader(infile)
            key, val = groups_db.fieldnames
            for item in groups_db :
                self.groups[item[key]] = item[val]
        # configuration
        cfg = configparser.ConfigParser()
        cfg.read(f"{path}/badass.cfg")
        self.cfg = cfgtree("MAIL", "REGISTRATION")
        for sec in cfg :
            for key, val in cfg[sec].items() :
                try :
                    self.cfg[sec][key] = ast.literal_eval(val or "None")
                except :
                    self.cfg[sec][key] = val
    def add_user (self, email, firstname, lastname, password, group, roles, studentid,
                  activated=False) :
        try :
            salt = secrets.token_hex()
            self.db.users.insert(email=email,
                                 firstname=firstname,
                                 lastname=lastname,
                                 password=salthash(salt, password),
                                 salt=salt,
                                 group=group,
                                 roles=roles,
                                 studentid=studentid,
                                 activated=activated)
            self.db.commit()
            return True
        except IntegrityError :
            return False
    def get_user_from_id (self, user_id) :
        row = self.db(self.db.users.id == user_id).select().first()
        return dict(row or {})
    def get_user_from_auth (self, email, password) :
        row = self.db(self.db.users.email == email).select().first()
        if not row :
            return {}
        fields = dict(row)
        if fields.pop("password") != salthash(fields.pop("salt"), password) :
            return {}
        if not fields["activated"] :
            row.update_record(activated=True)
            self.db.commit()
        return fields
    def del_user (self, email) :
        done = self.db(self.db.users.email == email).delete()
        self.db.commit()
        return done > 0
    def update_user (self, currentemail, **fields) :
        assert set(fields) <= {"email", "firstname", "lastname", "password",
                               "group", "roles", "studentid"}
        row = self.db(self.db.users.email == currentemail).select().first()
        if row is None :
            return False
        if "password" in fields :
            fields["password"] = salthash(row["salt"], fields["password"])
        row.update_record(**fields)
        self.db.commit()
        return True
    def iter_users (self) :
        for row in self.db().select(self.db.users.email,
                                    self.db.users.firstname,
                                    self.db.users.lastname,
                                    self.db.users.group,
                                    self.db.users.roles,
                                    self.db.users.studentid,
                                    self.db.users.activated) :
            yield dict(row)

class User (UserMixin) :
    db = None
    @classmethod
    def from_id (cls, user_id) :
        try :
            fields = cls.db.get_user_from_id(int(user_id))
            if not fields :
                return
            return cls(**fields)
        except :
            return
    @classmethod
    def from_auth (cls, email, password) :
        fields = cls.db.get_user_from_auth(email, password)
        if not fields :
            return
        fields["authenticated"] = True
        return cls(**fields)
    @classmethod
    def iter_users (cls) :
        for fields in cls.db.iter_users() :
            yield cls(**fields)
    def __init__ (self, **fields) :
        self.authenticated = False
        for key, val in fields.items() :
            setattr(self, key, val)
    @property
    def is_authenticated (self) :
        return self.authenticated
    @property
    def is_active (self) :
        return True
    @property
    def is_anonymous (self) :
        return False
    def get_id (self) :
        return str(self.id)
    def has_role (self, role) :
        return role in self.roles

class Role (object) :
    teacher = "teacher"
    admin = "admin"
    dev = "dev"

