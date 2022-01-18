import csv, secrets, configparser, ast

from pydal import DAL, Field
from sqlite3 import IntegrityError
from ..mkpass import salthash

class Roles (object) :
    def __init__ (self, cfg, values=["teacher", "admin", "dev"]) :
        self._cfg = cfg
        self._val = set(values)
        for val in values :
            setattr(self, val, val)
    def __contains__ (self, value) :
        return value in self._val
    def __iter__ (self) :
        yield from sorted(self._val)
    def from_code (self, code) :
        for key, val in self._cfg.CODES.items() :
            if val == code :
                return list(sorted(r for r in key.lower().split() if r in self))
        return []
    def from_form (self, form) :
        return list(sorted(r for r in self if form.get(f"role-{r}", False)))

class BaseUser (dict) :
    db = None
    _fields = {"id" : 0,
               "email" : None,
               "firstname" : None,
               "lastname" : None,
               "group" : None,
               "roles" : [],
               "studentid" : None,
               "activated" : False,
               "authenticated" : False}
    @classmethod
    def add (cls, email, firstname, lastname, password, group, roles, studentid,
             activated=False) :
        fields = {"email" : email,
                  "firstname" : firstname,
                  "lastname" : lastname,
                  "group" : group,
                  "roles" : list(sorted(roles)),
                  "studentid" : studentid,
                  "activated" : activated}
        salt = secrets.token_hex()
        try :
            cls.db.users.insert(password=salthash(salt, password),
                                 salt=salt,
                                 **fields)
        except :
            cls.db.rollback()
            raise
        else :
            cls.db.commit()
        return cls(**fields)
    @classmethod
    def from_id (cls, user_id) :
        fields = dict(cls.db(cls.db.users.id == user_id).select().first())
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
            try :
                row.update_record(activated=True)
            except :
                cls.db.rollback()
                raise
            else :
                cls.db.commit()
        fields["activated"] = fields["authenticated"] = True
        return cls(**fields)
    @classmethod
    def iter_users (cls) :
        for row in cls.db().select(cls.db.users.id,
                                   cls.db.users.email,
                                   cls.db.users.firstname,
                                   cls.db.users.lastname,
                                   cls.db.users.group,
                                   cls.db.users.roles,
                                   cls.db.users.studentid,
                                   cls.db.users.activated) :
            yield cls(**dict(row))
    def __init__ (self, **fields) :
        super().__init__()
        for key, default in self._fields.items() :
            self[key] = fields.get(key, default)
    def __getattr__ (self, name) :
        if name in self._fields :
            return self.get(name, self._fields.get(name))
    def __str__ (self) :
        return f"<User: id={self.id}>"
    def has_role (self, role) :
        return role in self.roles
    def delete (self) :
        try :
            done = self.db(self.db.users.email == self.email).delete()
        except :
            self.db.rollback()
            raise
        else :
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
        if "roles" in fields :
            fields["roles"] = list(sorted(fields["roles"]))
        try :
            row.update_record(**fields)
        except :
            self.db.rollback()
            raise
        else :
            self.db.commit()
        return True

class cfgtree (dict) :
    def __init__ (self, *keys) :
        for k in keys :
            self[k] = self.__class__()
    def __getitem__ (self, key) :
        return super().__getitem__(str(key).upper())
    def get (self, key, default=None) :
        return super().get(str(key).upper(), default)
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
                    Field("course", "string"),
                    Field("exercise", "string"),
                    Field("path", "string"))
    # configuration
    config = configparser.ConfigParser()
    config.read(f"{path}/badass.cfg")
    cfg = cfgtree("MAIL", "CODES", "GROUPS")
    for sec in config :
        for key, val in config[sec].items() :
            try :
                cfg[sec][key] = ast.literal_eval(val or "None")
            except :
                cfg[sec][key] = val
    class User (BaseUser) :
        pass
    User.db = db
    return db, cfg, User, Roles(cfg)
