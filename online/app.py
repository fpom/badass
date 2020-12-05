##
## users management
##

import hashlib, collections, time, pathlib, csv

def salthash (s, p) :
    salted = (s + p).encode("utf-8")
    return hashlib.sha512(salted).hexdigest()

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
        groups = set()
        bykey = {}
        with open(self.path, encoding="utf-8") as infile :
            self.fields = infile.readline().strip().split(",")
            self.key = self.fields[0]
            user = collections.namedtuple("user", self.fields)
            db = csv.DictReader(infile, self.fields)
            for item in db :
                row = user(**item)
                groups.add(row.group)
                bykey[getattr(row, self.key)] = row
        self.loaded = time.time()
        self._groups = list(sorted(groups))
        self.bykey = bykey
    def __getitem__ (self, key) :
        self.reload()
        return self.bykey[key]
    def auth (self, key, password) :
        self.reload()
        if "salt" not in self.fields :
            return self[key].password == password
        else :
            row = self[key]
            sh = salthash(row.salt, password)
            return sh == row.password

students = UserDB("data/students.csv")
teachers = UserDB("data/teachers.csv")

##
## flask app starts here
##

from flask import Flask, abort, current_app, request, url_for, render_template, flash, redirect, session, Markup, Response
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, InternalServerError
from datetime import datetime
from functools import wraps
import threading, subprocess, zipfile, json, uuid

app = Flask("badass-online")
app.secret_key = open("data/secret_key", "rb").read()

##
## asynchronous API for long running tasks
##

# inspired from https://stackoverflow.com/questions/31866796/making-an-asynchronous-task-in-flask

tasks = {}

@app.before_first_request
def before_first_request () :
    def clean_old_tasks () :
        global tasks
        while True :
            five_min_ago = datetime.timestamp(datetime.utcnow()) - 5 * 60
            tasks = {task_id : task for task_id, task in tasks.items()
                     if "completion_timestamp" not in task
                     or task["completion_timestamp"] > five_min_ago}
            time.sleep(60)
    thread = threading.Thread(target=clean_old_tasks)
    thread.start()

def wait_task (task_id, delay=3000) :
    status_url = url_for("gettaskstatus", task_id=task_id)
    return render_template("wait.html", status_url=status_url, status_wait=delay)

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
                except Exception :
                    tasks[task_id]["return_value"] = InternalServerError()
                    if current_app.debug :
                        raise
                finally :
                    now = datetime.timestamp(datetime.utcnow())
                    tasks[task_id]["completion_timestamp"] = now
        task_id = uuid.uuid4().hex
        tasks[task_id] = {"task_thread" :
                          threading.Thread(target=task_call,
                                           args=(current_app._get_current_object(),
                                                 request.environ))}
        tasks[task_id]["task_thread"].start()
        return wait_task(task_id)
    return new_function

@app.route("/status/<task_id>")
def gettaskstatus (task_id) :
    global tasks
    task = tasks.get(task_id, None)
    if task is None :
        abort(404)
    if "return_value" not in task :
        return wait_task(task_id)
    return task["return_value"]

##
## CSS & JS
##

@app.route("/assets/style.css")
def css () :
    resp = Response(render_template("style.css"), status=200, mimetype="text/css")
    resp.headers["Content-Type"] = "text/css; charset=utf-8"
    return resp

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
        assert students.auth(who.num, form.pop("password"))
    except :
        errors.append("numéro d'étudiant ou mot de passe incorrect")
    if form.pop("consent", None) != "on" :
        errors.append("vous devez certifier votre identité")
    if not request.files.getlist("source") :
        errors.append("fichier(s) source(s) manquant(s)")
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
    base = pathlib.Path("upload").joinpath(*entry)
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
    subprocess.run(["python", "-m", "badass", "run", script, project])
    with zipfile.ZipFile(project / "report.zip") as zf :
        with zf.open("report.json") as stream :
            report = json.load(stream)
        for test in report :
            with zf.open(test["html"]) as stream :
                test["html"] = stream.read().decode(encoding="utf-8", errors="replace")
            test["icon"] = _result_icons[test["status"]]
            for key in ("text", "html") :
                test[key] = Markup(test[key])
    return render_template("result.html", report=report)

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
        who = teachers[form.pop("login")]
        assert teachers.auth(who.login, form.pop("password"))
    except :
        flash("indentifiant ou mot de passe incorrect", "error")
        return redirect(url_for("teacher"))
    # process validated query
    session["search"] = {"course" : form["Course"],
                         "group" : form[form["Course"]],
                         "exercise" : request.form.getlist("exercise")}
    return redirect(url_for("report"))

@app.route("/report")
@async_api
def report () :
    search = session["search"]
    return search
