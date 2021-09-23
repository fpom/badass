import csv, secrets, configparser, ast

from pydal import DAL, Field
from sqlite3 import IntegrityError
from flask_login import UserMixin
from .mkpass import salthash

from enum import Enum

class Role (Enum) :
    teacher = "teacher"
    admin = "admin"
    dev = "dev"

class BaseUser (UserMixin) :
    db = None
    @classmethod
    def add (cls, email, firstname, lastname, password, group, roles, studentid,
             activated=False) :
        fields = {"email" : email,
                  "firstname" : firstname,
                  "lastname"  : lastname,
                  "group" : group,
                  "roles" : roles,
                  "studentid" : studentid,
                  "activated"  : activated}
        salt = secrets.token_hex()
        try :
            cls.db.users.insert(password=salthash(salt, password),
                                 salt=salt,
                                 **fields)
            cls.db.commit()
        except IntegrityError :
            return
        return cls(**fields)
    @classmethod
    def from_id (cls, user_id) :
        try :
            uid = int(user_id)
        except :
            return
        fields = dict(cls.db(cls.db.users.id == uid).select().first())
        if not fields :
            return
        return cls(**fields)
    @classmethod
    def from_email (cls, email) :
        fields = dict(cls.db(cls.db.users.email == email).select().first())
        if not fields :
            return
        return cls(**fields)
    @classmethod
    def from_auth (cls, email, password) :
        row = cls.db(cls.db.users.email == email).select().first()
        if not row :
            return
        fields = dict(row)
        if fields.pop("password") != salthash(fields.pop("salt"), password) :
            return
        if not fields["activated"] :
            row.update_record(activated=True)
            cls.db.commit()
        fields["authenticated"] = True
        return cls(**fields)
    @classmethod
    def iter_users (cls) :
        for row in cls.db().select(cls.db.users.email,
                                   cls.db.users.firstname,
                                   cls.db.users.lastname,
                                   cls.db.users.group,
                                   cls.db.users.roles,
                                   cls.db.users.studentid,
                                   cls.db.users.activated) :
            yield cls(**dict(fields))
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
    def delete (self) :
        done = self.db(self.db.users.email == self.email).delete()
        self.db.commit()
        return done > 0
    def update (self, **fields) :
        assert set(fields) <= {"email", "firstname", "lastname", "password",
                               "group", "roles", "studentid"}
        row = self.db(self.db.users.email == self.email).select().first()
        if not row :
            return False
        if "password" in fields :
            fields["password"] = salthash(row["salt"], fields["password"])
        row.update_record(**fields)
        self.db.commit()
        return True

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

def connect (path) :
    # sqlite DB
    db = DAL(f"sqlite://badass.sqlite", folder=path)
    db.define_table("users",
                    Field("email", "string", unique=True),
                    Field("firstname", "string"),
                    Field("lastname", "string"),
                    Field("password", "string"),
                    Field("salt", "string"),
                    Field("group", "string"),
                    Field("roles", "list:string"),
                    Field("studentid", "string"),
                    Field("activated", "boolean"))
    db.define_table("submissions",
                    Field("user", "reference users"),
                    Field("date", "datetime"),
                    Field("exercise", "string"),
                    Field("path", "string"))
    db.define_table("results",
                    Field("user", "reference users"),
                    Field("date", "datetime"),
                    Field("submission", "reference submissions"),
                    Field("savedto", "string"),
                    Field("permalink", "string"))
    db.define_table("reports",
                    Field("user", "reference users"),
                    Field("date", "datetime"),
                    Field("groups", "list:string"),
                    Field("exercises", "list:string"),
                    Field("path", "string"))
    # configuration
    config = configparser.ConfigParser()
    config.read(f"{path}/badass.cfg")
    cfg = cfgtree("MAIL", "REGISTRATION", "GROUPS")
    for sec in config :
        for key, val in config[sec].items() :
            try :
                cfg[sec][key] = ast.literal_eval(val or "None")
            except :
                cfg[sec][key] = val
    class User (BaseUser) :
        pass
    User.db = db
    return db, cfg, User, Role
