import collections, time, pathlib, csv, threading, subprocess, \
    zipfile, json, secrets, os, sys, mimetypes, random, itertools, traceback

from datetime import datetime
from functools import wraps
from pprint import pformat

from flask import Flask, abort, current_app, request, url_for, render_template, \
    flash, redirect, session, Markup, Response, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError

from pygments import highlight
from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import HtmlFormatter

from .mkpass import salthash, SALT

random.seed()

##
##
##

ENV = dict(os.environ)
ENV["PYTHONPATH"] = ":".join(sys.path)

UPLOAD = pathlib.Path("upload")
REPORT = pathlib.Path("reports")
ERROR = pathlib.Path("errors")

TEMPLATES = pathlib.Path("templates")
if not all ((TEMPLATES / tpl).exists() for tpl in
            ("index.html", "result.html", "style.css", "teacher.html", "wait.html")) :
    TEMPLATES = str(pathlib.Path(__file__).parent / "templates")

##
## users management
##

class UserDB (object) :
    def __init__ (self, path) :
        self.path = pathlib.Path(path)
        self.loaded = 0
        self.reload()
    @property
    def groups (self) :
        self.reload()
        return self._groups
    def reload (self) :
        if self.loaded > self.path.stat().st_mtime :
            return
        groups = {}
        bykey = {}
        with open(self.path, encoding="utf-8") as infile :
            self.fields = infile.readline().strip().split(",")
            self.key = self.fields[0]
            user = collections.namedtuple("user", self.fields)
            db = csv.DictReader(infile, self.fields)
            for item in db :
                item["group"] = item["group"].replace(" ", "_")
                row = user(**item)
                key = getattr(row, self.key)
                if row.group not in groups :
                    groups[row.group] = []
                groups[row.group].append(key)
                bykey[key] = row
        self.loaded = time.time()
        self._groups = groups
        self._bykey = bykey
    def __getitem__ (self, key) :
        self.reload()
        return self._bykey[key]
    def auth (self, key, password) :
        self.reload()
        row = self[key]
        if "salt" not in self.fields :
            attempt, _ = password, salthash(SALT, password)
        else :
            _, attempt = password, salthash(row.salt, password)
        return secrets.compare_digest(attempt, row.password)

students = UserDB("data/students.csv")
teachers = UserDB("data/teachers.csv")

##
## waiting animations
##

ANIMS = [json.load(path.open(encoding="utf-8"))
         for path in pathlib.Path().glob("anim/*.json")] or [None]

##
## flask app starts here
##

app = Flask("badass-online", template_folder=TEMPLATES)
app.secret_key = open("data/secret_key", "rb").read()

##
## errors handling
##

def errorpath () :
    for size in itertools.count(start=2) :
        for i in range(10) :
            path = ERROR / secrets.token_urlsafe(size)
            if not path.exists() :
                return path

@app.errorhandler(Exception)
def handle_exception (err) :
    if not isinstance(err, HTTPException) :
        path = errorpath()
        name = path.name
        with path.open("w", encoding="utf-8") as out :
            tb = traceback.TracebackException.from_exception(err, capture_locals=True)
            out.write("<h5>Traceback</h5>\n")
            text = "".join(tb.format())
            out.write(highlight(text, PythonTracebackLexer(), HtmlFormatter()))
            if session :
                out.write("<h5>Session</h5><div>")
                for key, val in session.items() :
                    out.write(f"<b><code>{key}</code></b><pre>\n")
                    try :
                        text = pformat(val)
                    except :
                        text = repr(val)
                    out.write(highlight(text, PythonLexer(), HtmlFormatter()))
                out.write("</div>")
        err = InternalServerError(f"The server encountered an internal error"
                                  f" and was unable to complete your request."
                                  f" The error has been recorded with identifier"
                                  f" {name!r} and will be investigated.")
    return render_template("httperror.html", err=err), err.code

@app.route("/error", methods=["GET", "POST"])
def error () :
    if request.method == "GET" :
        return render_template("error.html", report=None, form={})
    form = dict(request.form)
    try :
        who = teachers[form["login"]]
        if not teachers.auth(who.login, form["password"]) :
            raise Exception()
        if who.group != "admin" :
            raise Exception()
    except :
        flash("access denied", "error")
        return render_template("error.html", report=None, form=form)
    try :
        if not form["error"] :
            raise Exception()
        path = ERROR / form["error"]
        report = path.read_text(encoding="utf-8")
    except :
        flash(f"invalid error identifier {form.pop('error','')!r}", "error")
        return render_template("error.html", report=None, form=form)
    if form.get("delete", None) == "on" :
        path.unlink()
        form.pop("error", None)
    return render_template("error.html", report=Markup(report), form=form)

##
## asynchronous API for long running tasks
##

tasks = {}

@app.before_first_request
def before_first_request () :
    def clean_old_tasks () :
        global tasks
        while True :
            time.sleep(60)
            five_min_ago = datetime.timestamp(datetime.utcnow()) - 300
            for task_id, task in list(tasks.items()) :
                if task.get("completion_timestamp", five_min_ago) < five_min_ago :
                    print(f" # Dropping task {task_id}")
                    del tasks[task_id]
    thread = threading.Thread(target=clean_old_tasks)
    thread.start()

def async_api (wrapped_function) :
    @wraps(wrapped_function)
    def new_function (*args, **kwargs) :
        global tasks
        def task_call (flask_app, environ) :
            global tasks
            with flask_app.request_context(environ) :
                try :
                    tasks[task_id]["return_value"] = wrapped_function(*args, **kwargs)
                except HTTPException as e :
                    tasks[task_id]["return_value"] = current_app.handle_http_exception(e)
                except Exception as err :
                    tasks[task_id]["return_value"] = handle_exception(err)
                finally :
                    now = datetime.timestamp(datetime.utcnow())
                    tasks[task_id]["completion_timestamp"] = now
        task_id = secrets.token_urlsafe()
        tasks[task_id] = {"task_thread" :
                          threading.Thread(target=task_call,
                                           args=(current_app._get_current_object(),
                                                 request.environ))}
        tasks[task_id]["task_thread"].start()
        return render_template("wait.html",
                               status_url=url_for("gettaskstatus", task_id=task_id),
                               anim=random.choice(ANIMS))
    return new_function

@app.route("/status/<task_id>")
def gettaskstatus (task_id) :
    global tasks
    task = tasks.get(task_id, None)
    if task is None :
        abort(404)
    if "return_value" in task :
        return jsonify({"wait" : False,
                        "link" : url_for("gettaskresult", task_id=task_id)})
    else :
        return jsonify({"wait" : True})

@app.route("/result/<task_id>")
def gettaskresult (task_id) :
    global tasks
    task = tasks.get(task_id, None)
    if task is None :
        abort(404)
    return task.get("return_value")

##
## static assets
##

DATADIR = pathlib.Path(__file__).parent
STATIC = DATADIR / "static"

@app.route("/<kind>/<path:name>")
def asset (kind, name) :
    mime, _ = mimetypes.guess_type(name)
    if mime is None :
        mime = "application/octet-stream"
    if kind == "t" :
        resp = Response(render_template(name), status=200, mimetype=mime)
        resp.headers["Content-Type"] = f"{mime}; charset=utf-8"
        return resp
    elif kind == "s" :
        if mime.startswith("text/") :
            data = (STATIC / name).read_text(encoding="utf-8")
            resp = Response(data, status=200, mimetype=mime)
            resp.headers["Content-Type"] = f"{mime}; charset=utf-8"
        else :
            data = (STATIC / name).read_bytes()
            resp = Response(data, status=200, mimetype=mime)
            resp.headers["Content-Type"] = f"{mime}"
        return resp
    else :
        abort(404)

##
## students interface
##

@app.route("/", methods=["GET", "POST"])
def index () :
    if request.method == "GET" :
        # show form if not provided
        return render_template("index.html")
    # check form content
    errors = []
    form = dict(request.form)
    try :
        who = students[form["student"]]
        if not students.auth(who.num, form.pop("password")) :
            raise Exception()
    except :
        errors.append("invalid student's number or password")
    if form.pop("consent", None) != "on" :
        errors.append("you must certify your identity")
    if not request.files.getlist("source") :
        errors.append("missing source files(s)")
    if errors :
        for msg in errors :
            flash(msg, "error")
        return redirect(url_for("index"))
    # process validated query
    session["form"] = form
    # build unique dir for submission
    entry = [form["Course"]]
    while entry[-1] in form :
        entry.append(form[entry[-1]])
    now = datetime.now()
    entry.extend([form["student"],
                  now.strftime("%Y-%m-%d"),
                  now.strftime("%H:%M:%S.%f")])
    base = UPLOAD.joinpath(*entry)
    form["base"] = str(base)
    base /= "src"
    base.mkdir(parents=True, exist_ok=True)
    # save files
    form["source"] = []
    for src in request.files.getlist("source") :
        name = secure_filename(src.filename)
        path = str(base / name)
        form["source"].append(name)
        src.save(path)
    # go process the submission
    return redirect(url_for("result"))

_result_icons = {"fail" : "delete",
                 "warn" : "info",
                 "pass" : "check"}

@app.route("/result")
@async_api
def result () :
    script = pathlib.Path(session["form"]["path"])
    project = pathlib.Path(session["form"]["base"])
    subprocess.run(["python3", "-m", "badass", "run", script, project],
                   env=ENV)
    with zipfile.ZipFile(project / "report.zip") as zf :
        with zf.open("report.json") as stream :
            report = json.load(stream)
        for test in report :
            with zf.open(test["html"]) as stream :
                test["html"] = stream.read().decode(encoding="utf-8", errors="replace")
            test["icon"] = _result_icons[test["status"]]
            for key in ("text", "html") :
                test[key] = Markup(test[key])
    data = render_template("result.html", report=report)
    path = REPORT / secrets.token_urlsafe()
    while path.exists() :
        path = REPORT / secrets.token_urlsafe()
    with path.open("w") as out :
        out.write(data)
    permalink = url_for("report", name=str(path.name), _external=True)
    permalink_path = project / "permalink"
    with permalink_path.open("w", encoding="utf-8") as out :
        out.write(permalink)
    return redirect(permalink)

@app.route("/report/<name>")
def report (name) :
    path = REPORT / name
    if path.exists() :
        return path.read_text(encoding="utf-8")
    else :
        abort(404)

##
## teachers interface
##

@app.route("/teacher", methods=["GET", "POST"])
def teacher () :
    if request.method == "GET" :
        return render_template("teacher.html")
    # check form content
    form = dict(request.form)
    try :
        who = teachers[form["login"]]
        if not teachers.auth(who.login, form.pop("password")) :
            raise Exception()
    except :
        flash("invalid login or password", "error")
        return redirect(url_for("teacher"))
    # process validated query
    session["form"] = form
    return redirect(url_for("marks"))

@app.route("/marks")
@async_api
def marks () :
    form = session["form"]
    entry = [form["Course"]]
    while entry[-1] in form :
        entry.append(form[entry[-1]])
    group = entry.pop(-1)
    entry.append(form["exercise"])
    base = UPLOAD.joinpath(*entry)
    now = datetime.now().strftime("%Y-%m-%d---%H-%M-%S")
    path = UPLOAD / form["login"] / f"{group}---{now}.zip"
    path.parent.mkdir(exist_ok=True, parents=True)
    subprocess.check_output(["python3", "-m", "badass", "report",
                             "-p", path, "-b", base] + students.groups[group],
                            env=ENV)
    return send_file(path, as_attachment=True, attachment_filename=path.name)
