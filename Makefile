install:
	pip install . --no-deps --force --use-feature=in-tree-build
	make clean

pip: clean
	python3 setup.py bdist_wheel
	python3 -m twine upload dist/*
	make clean

test:
	make install
	badass www -i test
	python3 test-data/mktest.py
	cp -r test-data/upload test/
	make -C test serve

retest:
	rm -rf test
	make test

clean:
	rm -rf build dist not_so_badass.egg-info
