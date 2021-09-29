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
	badass www -a test/data \
		--email foo@spam \
		--first-name Foo \
		--last-name Spammer \
		--group TEST \
		--student-id 1234 \
		--no-roles \
		--password FOO@sp4m \
		--no-activated
	badass www -a test/data \
                --email bar@nospam \
                --first-name Bar \
                --last-name Tsimpson \
                --no-group \
                --no-student-id \
                --role dev --role admin --role teacher \
                --password BAR@n0sp4m \
		--no-activated
	make -C test serve

retest:
	rm -rf test
	make test

clean:
	rm -rf build dist not_so_badass.egg-info
