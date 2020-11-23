serve: static/index.js static/teacher.js
	FLASK_APP=app.py WERKZEUG_DEBUG_PIN=off FLASK_ENV=development flask run

static/%.js: forms/%.yaml
	python genform.py -o $@ $<

clean:
	rm -rf $$(find . -type f -name "*~") $$(find . -type d -name __pycache__)

distclean: clean
	rm -rf upload/*
