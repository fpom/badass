install:
	python3 setup.py install
	make clean

pip: clean
	python3 setup.py bdist_wheel
	python3 -m twine upload dist/*
	make clean

clean:
	rm -rf build dist not_so_badass.egg-info
