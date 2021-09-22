import collections, time, pathlib, csv, threading, subprocess, \
    zipfile, json, secrets, os, sys, mimetypes, random, itertools, traceback

from datetime import datetime
from functools import wraps
from pprint import pformat

from flask import Flask, abort, current_app, request, url_for, render_template, \
    flash, redirect, session, Markup, Response, send_file, jsonify
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError

from flask_login import LoginManager
from flask_mail import Mail, Message

from pygments import highlight
from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import HtmlFormatter

from .db import BadassDB, User, Role
from .mkpass import pwgen

import badass

random.seed()

##
## config
##

BADASS = str(pathlib.Path(badass.__file__).parent.parent).rstrip("/") + "/"
STDLIB = str(pathlib.Path(os.__file__).parent.parent).rstrip("/") + "/"

ENV = dict(os.environ)
ENV["PYTHONPATH"] = ":".join(sys.path)

UPLOAD = pathlib.Path("upload")
UPLOAD.mkdir(exist_ok=True, parents=True)
REPORT = pathlib.Path("reports")
REPORT.mkdir(exist_ok=True, parents=True)
ERROR = pathlib.Path("errors")
ERROR.mkdir(exist_ok=True, parents=True)

BADASSTPL = pathlib.Path(BADASS) / "www" / "templates"
TEMPLATES = pathlib.Path("templates")
if not all((TEMPLATES / tpl.name).exists() for tpl in
           itertools.chain(BADASSTPL.glob("*.html"), BADASSTPL.glob("*.css"))) :
    TEMPLATES = BADASSTPL

ANIMS = [json.load(path.open(encoding="utf-8"))
         for path in pathlib.Path().glob("anim/*.json")] or [None]

db = User.db = BadassDB("data")
##
## flask app starts here
##

app = Flask("badass-online", template_folder=TEMPLATES)
app.secret_key = open("data/secret_key", "rb").read()

for key, val in db.cfg.items("MAIL") :
    app.config[key] = val

mail = Mail(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user (user_id) :
    return User.load(user_id)

##
## authentication
##

def enforce_auth (func) :
    @wraps(func)
    def wrapper (*l, **k) :
        if not current_user.is_authenticated :
            return redirect(url_for("login"))
        return func(*l, **k)
    return wrapper

def require_login (func) :
    @wraps(func)
    def wrapper (*l, **k) :
        if not current_user.is_authenticated :
            abort(401)
        return func(*l, **k)
    return wrapper

def require_role (role) :
    def decorator (func) :
        @wraps(func)
        def wrapper (*l, **k) :
            if not (current_user.is_authenticated and current_user.has_role(role)) :
                abort(401)
            return func(*l, **k)
        return wrapper
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login () :
    if request.method == "GET" :
        return render_template("login.html")
    form = dict(request.form)
    user = User.from_auth(form.get("email", "").strip().lower(),
                          form.get("password", ""))
    login_user(user)
    return redirect(url_for("index"))

@app.route("/logout")
@enforce_auth
def logout () :
    logout_user()
    return redirect(url_for("index"))

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
@require_login
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
@require_login
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
## user management
##

@app.route("/register", methods=["GET", "POST"])
def register () :
    if request.method == "GET" :
        return render_template("register.html",
                               groups=db.groups,
                               code=bool(db.cfg.REGISTRATION.PASSWORD))
    form = dict(request.form)
    if (db.cfg.REGISTRATION.PASSWORD
        and form.get("code", None) != db.cfg.REGISTRATION.PASSWORD) :
        flash("invalid course code", "error")
        abort(401)
    errors = []
    for field, desc in [("email", "e-mail"),
                        ("firstname", "first name"),
                        ("lastname", "last name"),
                        ("studentid", "student number")] :
        if not form.get(field, None) :
            errors.append(f"{desc} is required")
    if form.get("group", None) not in db.groups :
        errors.append("invalid group")
    if errors :
        for msg in errors :
            flash(msg, "error")
        return render_template("register.html",
                               groups=db.groups,
                               code=bool(db.cfg.REGISTRATION.PASSWORD))
    password = pwgen()
    if db.add_user(email=form["email"],
                   firstname=form["firstname"],
                   lastname=form["lastname"],
                   password=password,
                   group=form["group"],
                   roles=[],
                   studentid=int(form["studentid"])) :
        flash(f"registration succeeded, your password has been"
              f" emailed to {form['email']}", "info")
        mail.send(Message(f"Your password is {password}\n",
                          subject="Welcome to badass",
                          recipients=[form["email"]]))
        return redirect(url_for("index"))
    else :
        flash("registration failed, this e-mail may be used already", "error")
        return redirect(url_for("register"))

@app.route("/reset")
def reset () :
    if request.method == "GET" :
        return render_template("reset.html", code=bool(db.cfg.REGISTRATION.PASSWORD))
    form = dict(request.form)
    if (db.cfg.REGISTRATION.PASSWORD
        and form.get("code") != db.cfg.REGISTRATION.PASSWORD) :
        flash("invalid course code", "error")
        abort(401)
    if not form.get("email", None) :
        flash("e-mail is required", "error")
        return render_template("reset.html", code=bool(db.cfg.REGISTRATION.PASSWORD))
    password = pwgen()
    if db.update_user(form["email"], password=password) :
        flash(f"your password has been emailed to {form['email']}", "info")
        mail.send(Message(f"Your new password is {password}\n",
                          subject="Welcome back to badass",
                          recipients=[form["email"]]))
        return redirect(url_for("index"))
    else :
        flash("password reset failed, this e-mail may be invalid", "error")
        return redirect(url_for("reset"))

@app.route("/users")
#@require_role(Role.admin)
def users () :
    return render_template("users.html", users=User.iter_users())

@app.route("/user/<user_id>")
@require_login
def user (user_id) :
    pass

##
## submission interface
##

@app.route("/", methods=["GET", "POST"])
@enforce_auth
def index () :
    if request.method == "GET" :
        return render_template("index.html")
    # check form
    errors = []
    form = dict(request.form)
    if form.pop("consent", None) != "on" :
        errors.append("you must certify your identity")
    if not request.files.getlist("source") :
        errors.append("missing source files(s)")
    if any(not src.filename for src in request.files.getlist("source")) :
        errors.append("missing source files(s)")
    if errors :
        for msg in errors :
            flash(msg, "error")
        return redirect(url_for("index"))
    # process validated query
    session["form"] = form
    # build unique dir for submission
    entry = [form.pop("Course")]
    while entry[-1] in form :
        entry.append(form.pop(entry[-1]))
    now = datetime.now()
    entry.extend([form.pop("student"),
                  now.strftime("%Y-%m-%d"),
                  now.strftime("%H:%M:%S.%f")])
    base = UPLOAD.joinpath(*entry)
    form["base"] = str(base)
    base /= "src"
    base.mkdir(parents=True, exist_ok=True)
    # save files
    for src in request.files.getlist("source") :
        name = secure_filename(src.filename)
        path = str(base / name)
        src.save(path)
    # TODO: save submission to DB
    # go process the submission
    return redirect(url_for("result"))

_result_icons = {"fail" : "delete",
                 "warn" : "info",
                 "pass" : "check"}

def check_output (*l, **k) :
    proc = subprocess.run(*l, **k, capture_output=True)
    proc.check_returncode()

@app.route("/result")
@async_api
@require_login
def result () :
    form = session["form"]
    script = pathlib.Path(form.pop("path"))
    project = pathlib.Path(form.pop("base"))
    define = []
    for key, val in form.items() :
        define.extend(["-d", f"{key}={val}"])
    check_output(["python3", "-m", "badass", "run", script, project] + define,
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
    # TODO: save result to DB
    return redirect(permalink)

@app.route("/report/<name>")
@enforce_auth
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
@enforce_auth
@require_role(Role.teacher)
def teacher () :
    # TODO : add list of previous reports
    if request.method == "GET" :
        return render_template("teacher.html")
    # process validated query
    form["group"] = request.form.getlist("group")
    form["exercise"] = request.form.getlist("exercise")
    session["form"] = form
    return redirect(url_for("marks"))

@app.route("/marks")
@async_api
@require_login
def marks () :
    form = session["form"]
    base = UPLOAD.joinpath(form["Course"])
    now = datetime.now().strftime("%Y-%m-%d---%H-%M-%S")
    group = "-".join(sorted(form["group"]))
    path = UPLOAD / form["login"] / f"{group}---{now}.zip"
    path.parent.mkdir(exist_ok=True, parents=True)
    argv = ["python3", "-m", "badass", "report", "-p", path, "-b", base]
    for exo in form["exercise"] :
        argv.extend(["-e", exo])
    for grp in list(form["group"]) :
        argv.extend(students.groups[grp.replace(" ", "_")])
    check_output(argv, env=ENV)
    # TODO : redirect to /teacher and flash link to new report
    return send_file(path.open("rb"), as_attachment=True, attachment_filename=path.name)

##
## errors handling
##

def errorpath () :
    for size in itertools.count(start=2) :
        for i in range(10) :
            path = ERROR / secrets.token_urlsafe(size)
            if not path.exists() :
                return path

# @app.errorhandler(Exception)
# def handle_exception (err) :
#     if not isinstance(err, HTTPException) :
#         path = errorpath()
#         name = path.name
#         with path.open("w", encoding="utf-8") as out :
#             tb = traceback.TracebackException.from_exception(err, capture_locals=True)
#             out.write("<h5>Traceback</h5>\n")
#             text = "".join(tb.format()).replace(BADASS, "").replace(STDLIB, "")
#             out.write(highlight(text, PythonTracebackLexer(), HtmlFormatter()))
#             if session :
#                 out.write("<h5>Session</h5><div>")
#                 for key, val in session.items() :
#                     out.write(f"<b><code>{key}</code></b><pre>\n")
#                     try :
#                         text = pformat(val)
#                     except :
#                         text = repr(val)
#                     out.write(highlight(text, PythonLexer(), HtmlFormatter()))
#                 out.write("</div>")
#         err = InternalServerError(f"The server encountered an internal error"
#                                   f" and was unable to complete your request."
#                                   f" The error has been recorded with identifier"
#                                   f" {name!r} and will be investigated.")
#     return render_template("httperror.html", err=err), err.code

@app.route("/errors", methods=["GET", "POST"])
@enforce_auth
@require_role(Role.dev)
def error () :
    if request.method == "GET" :
        return render_template("error.html", report=None, form={})
    form = dict(request.form)
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

