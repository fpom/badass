import collections, time, pathlib, csv, threading, zipfile, json, subprocess, \
    secrets, os, sys, mimetypes, random, itertools, traceback, re, ast

from operator import or_
from datetime import datetime
from functools import wraps, reduce
from pprint import pformat

from flask import Flask, abort, current_app, request, url_for, render_template, \
    flash, redirect, session, Markup, Response, send_file, jsonify, g
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError
from werkzeug.middleware.proxy_fix import ProxyFix

from pygments import highlight
from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import HtmlFormatter

from ..db import connect
from ..mkpass import pwgen

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

DB, CFG, USER, ROLES = connect("data")

##
## flask app starts here
##

app = Flask("badass-online", template_folder=TEMPLATES)
app.secret_key = open("data/secret_key", "rb").read()
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

##
## authentication
##

@app.before_request
def load_user():
    if "user" in session:
        g.user = USER(**session["user"])
    else :
        g.user = USER()

def check_auth (*l, ROLE=None, ERROR=None, **k) :
    load_user()
    if not g.user.authenticated or (ROLE and not g.user.has_role(ROLE)) :
        if ERROR :
            abort(ERROR)
        else :
            return redirect(url_for(*l, **k))

def enforce_auth (func) :
    @wraps(func)
    def wrapper (*l, **k) :
        return check_auth("login") or func(*l, **k)
    return wrapper

def require_login (func) :
    @wraps(func)
    def wrapper (*l, **k) :
        return check_auth(ERROR=401) or func(*l, **k)
    return wrapper

def require_role (role) :
    def decorator (func) :
        @wraps(func)
        def wrapper (*l, **k) :
            return check_auth(ROLE=role, ERROR=401) or func(*l, **k)
        return wrapper
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login () :
    if request.method == "GET" :
        return render_template("login.html")
    form = dict(request.form)
    user = USER.from_auth(form.get("email", "").strip().lower(),
                          form.get("password", ""))
    if user is None :
        flash("invalid email or password", "error")
        return redirect(url_for("login"))
    g.user = session["user"] = user
    flash(f"logged in as {user.email}", "info")
    if g.user.has_role("teacher") :
        return redirect(url_for("teacher"))
    elif g.user.has_role("admin") :
        return redirect(url_for("users"))
    elif g.user.has_role("dev") :
        return redirect(url_for("errors"))
    else :
        return redirect(url_for("index"))

@app.route("/logout")
@enforce_auth
def logout () :
    session.pop("user", None)
    g.pop("user", None)
    flash("logged out", "info")
    return redirect(url_for("login"))

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
    check_auth(ERROR=401)
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
    check_auth(ERROR=401)
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
                               groups=CFG.GROUPS)
    code = request.form.get("code", None)
    if not any(code == c for c in CFG.CODES.values()) :
        flash("invalid course code", "error")
        return redirect(url_for("register"))
    roles = ROLES.from_code(code)
    errors = []
    for field, desc in [("email", "e-mail"),
                        ("firstname", "first name"),
                        ("lastname", "last name")] :
        if not request.form.get(field, None) :
            errors.append(f"{desc} is required")
    if not request.form.get("studentid", None) and not roles :
        errors.append("student number is required")
    if request.form.get("group", None) not in CFG.GROUPS and not roles :
        errors.append("invalid group")
    if errors :
        for msg in errors :
            flash(msg, "error")
        return render_template("register.html",
                               groups=CFG.GROUPS)
    password = pwgen()
    if USER.add(email=request.form["email"].strip().lower(),
                firstname=request.form["firstname"],
                lastname=request.form["lastname"],
                password=password,
                group=request.form.get("group", ""),
                roles=roles,
                studentid=request.form.get("studentid", "")) :
        flash(Markup(f"your password is <tt>{password}</tt>"), "info")
        return redirect(url_for("index"))
    else :
        flash("registration failed: this e-mail may be used already", "error")
        return redirect(url_for("register"))

@app.route("/users")
@require_role(ROLES.admin)
def users () :
    return render_template("users.html",
                           users=USER.iter_users(),
                           groups=CFG.GROUPS)

@app.route("/user/<user_id>", methods=["GET", "POST"])
@require_login
def user (user_id) :
    if not (str(g.user.id) == str(user_id) or g.user.has_role("admin")) :
        abort(401)
    if request.method == "GET" :
        return render_template("account.html",
                               user=USER.from_id(user_id),
                               groups=CFG.GROUPS,
                               roles=list(ROLES))
    user = USER.from_id(user_id)
    update = {}
    if g.user.has_role("admin") and request.form.get("password", False) :
        update["password"] = pwgen()
    for key in ("email", "firstname", "lastname", "group", "studentid") :
        new = request.form.get(key, None)
        if new and new != user[key] :
            update[key] = new
    if g.user.has_role("admin") :
        newroles = ROLES.from_form(request.form)
        if set(newroles) != set(user.roles) :
            update["roles"] = newroles
    if not update :
        flash("no account update required", "warning")
    elif user.update(**update) :
        if "password" in update :
            flash(Markup(f"account updated,"
                         f" new password is <tt>{update['password']}</tt>"),
                  "info")
        else :
            flash("account updated", "info")
    else :
        flash("could not update account", "error")
    return redirect(url_for("user", user_id=user_id))

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
    form["debug"] = form.pop("debug", None) == "on"
    files = list(request.files.getlist("source"))
    if not (files and all (src.filename for src in files)) :
        errors.append("missing source files(s)")
    if errors :
        for msg in errors :
            flash(msg, "error")
        return redirect(url_for("index"))
    # process validated query
    session["form"] = form
    # build unique dir for submission
    course = form.pop("Course")
    entry = [course]
    while entry[-1] in form :
        entry.append(form.pop(entry[-1]))
    exo = "/".join(entry[1:])
    now = datetime.now()
    entry.extend([str(g.user.id),
                  now.strftime("%Y-%m-%d"),
                  now.strftime("%H:%M:%S.%f")])
    base = UPLOAD.joinpath(*entry)
    form["base"] = str(base)
    srcpath = base / "src"
    srcpath.mkdir(parents=True, exist_ok=True)
    # save files
    for src in files :
        src.save(str(srcpath / secure_filename(src.filename)))
    # save submission to DB
    try :
        form["subid"] = DB.submissions.insert(user=g.user.id,
                                              date=now,
                                              course=course,
                                              exercise=exo,
                                              path=str(base))
    except :
        DB.rollback()
        raise
    else :
        DB.commit()
    # go process the submission
    flash("your submission has been recorded", "info")
    return redirect(url_for("result"))

_result_icons = {"fail" : "delete",
                 "warn" : "info",
                 "pass" : "check"}

def check_output (*l, **k) :
    logpath = k.pop("log", None)
    proc = subprocess.run(*l, **k, check=True, capture_output=True)
    if logpath :
        with open(logpath, "wb") as out :
            out.write(b"<h5>STDOUT</h5>\n"
                      b"<pre>\n")
            out.write(proc.stdout)
            out.write(b"</pre>\n"
                      b"<h5>STDERR</h5>\n"
                      b"<pre>\n")
            out.write(proc.stderr)
            out.write(b"</pre>\n")

@app.route("/result")
@async_api
def result () :
    check_auth(ERROR=401)
    form = session["form"]
    script = pathlib.Path(form.pop("path"))
    project = pathlib.Path(form.pop("base"))
    define = []
    logpath = None
    if form.get("debug", False) :
        logpath = errorpath(".dbg")
        define.append("--debug")
    for key, val in form.items() :
        define.extend(["-d", f"{key}={val}"])
    check_output(["python3", "-m", "badass", "run", script, project] + define,
                 env=ENV, log=logpath)
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
    # redirect to report
    return redirect(permalink)

@app.route("/report/<name>")
@enforce_auth
def report (name) :
    path = REPORT / name
    if path.exists() :
        if not path.suffix :
            return path.read_text(encoding="utf-8")
        else :
            return send_file(path.open("rb"),
                             as_attachment=True,
                             attachment_filename=path.name)
    else :
        abort(404)

##
## teachers interface
##

@app.route('/teacher/', defaults={"path" : None}, methods=["GET", "POST"])
@app.route("/teacher/<path>", methods=["GET"])
@enforce_auth
@require_role(ROLES.teacher)
def teacher (path) :
    groups = set()
    exos = collections.defaultdict(set)
    for row in DB(DB.users.id == DB.submissions.user).select(DB.users.group,
                                                             DB.submissions.course,
                                                             DB.submissions.exercise) :
        groups.add(row.users.group)
        exos[row.submissions.course].add(row.submissions.exercise)
    if request.method == "GET" :
        if path :
            url = url_for("report", name=path)
            flash(Markup(f'<a href="{url}" data-ajax="false">download report</a>'),
                  "info")
        return render_template("teacher.html",
                               groups={k : v for k, v in CFG.GROUPS.items()
                                       if k in groups},
                               exercises=exos)
    session["groups"] = grp = []
    session["exos"] = exo = []
    for key, val in request.form.items() :
        if val != "on" :
            continue
        elif key.startswith("grp-") :
            grp.append(key[4:])
        elif key.startswith("exo-") :
            exo.append(key[4:].replace("-", "/", 1))
    return redirect(url_for("marks"))

@app.route("/marks")
@async_api
def marks () :
    check_auth(ROLE=ROLES.teacher, ERROR=401)
    path = (REPORT / secrets.token_urlsafe()).with_suffix(".zip")
    while path.exists() :
        path = (REPORT / secrets.token_urlsafe()).with_suffix(".zip")
    path.parent.mkdir(exist_ok=True, parents=True)
    exos = session["exos"]
    argv = (["python3", "-m", "badass", "report", "-o", path]
            + ["-d", "data"]
            + ["-g"] + list(session["groups"])
            + ["-e"] + list(session["exos"]))
    check_output(argv, env=ENV)
    return redirect(url_for("teacher", path=str(path.name)))

##
## errors handling
##

def errorpath (suffix="") :
    for size in itertools.count(start=2) :
        for i in range(10) :
            path = (ERROR / secrets.token_urlsafe(size)).with_suffix(suffix)
            if not path.exists() :
                try :
                    path.open("x")
                except :
                    pass
                else :
                    return path

_tb = re.compile(r"b(['\"])Traceback \(most recent call last\):(.|\\\1|\1\1\1)*(\1)")

def format_tb (txt, out) :
    unique = {}
    for match in _tb.finditer(txt) :
        matched = match.group()
        unique[matched] = ast.literal_eval(matched)
    for num, (match, pystr) in enumerate(unique.items(), 1) :
        txt = txt.replace(match, f"{match[1]}SEE TRACEBACK #{num}{match[1]}")
    out.write('<div data-role="footer"><h5>TRACEBACK #0</h5></div>\n')
    out.write(highlight(txt, PythonTracebackLexer(), HtmlFormatter()))
    for num, (match, pystr) in enumerate(unique.items(), 1) :
        out.write(f'<div data-role="footer"><h5>TRACEBACK #{num}</h5></div>\n')
        out.write(highlight(pystr, PythonTracebackLexer(), HtmlFormatter()))

def handle_exception (err) :
    if not isinstance(err, HTTPException) :
        path = errorpath()
        name = path.name
        with path.open("w", encoding="utf-8") as out :
            tb = traceback.TracebackException.from_exception(err,
                                                             capture_locals=True)
            text = "".join(tb.format()).replace(BADASS, "").replace(STDLIB, "")
            format_tb(text, out)
            if session :
                out.write('<div data-role="footer"><h5>SESSION</h5></div><div>')
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

if not app.config["DEBUG"] :
    handle_exception = app.errorhandler(Exception)(handle_exception)

@app.route("/errors")
@enforce_auth
@require_role(ROLES.dev)
def errors () :
    err = []
    for path in ERROR.glob("*") :
        err.append(path.name)
    return render_template("errors.html", errors=err)

@app.route("/error/<ident>/<action>")
@enforce_auth
@require_role(ROLES.dev)
def error (ident, action) :
    err = ERROR / ident
    if not err.exists() :
        abort(404)
    elif action == "delete" :
        err.unlink()
        return redirect(url_for("errors"))
    elif action == "show" :
        txt = err.read_text(encoding="utf-8")
        return render_template("error.html", report=Markup(txt), error=err.name)
    else :
        abort(404)
