import ast, pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.absolute()
long_description = (here / "README.md").read_text(encoding="utf-8")

for line in (here / "badass" / "__init__.py").read_text(encoding="utf-8").splitlines() :
    if line.startswith("version =") :
        version = ast.literal_eval(line.split("=")[-1].strip())
        break
else :
    raise Exception("could not find version")

root = pathlib.Path("badass")

def walk (path=None) :
    if path is None :
        path = root
    for child in path.iterdir() :
        if child.is_dir() :
            if child.name != "__pycache__" :
                yield from walk(child)
        elif (child.is_file()
              and child.suffix in (".bad", ".yaml", ".json", ".cfg",
                                   ".svg", ".ico", ".gif", ".png", ".mp4",
                                   ".js", ".css", ".html", ".map", ".csv")) :
            yield str(child.relative_to(root))

data = list(walk())

tslib = root / "lang" / "tslib.so"
if not tslib.exists() :
    import runpy
    runpy.run_path("mktslibs.py")

data.append(str(tslib.relative_to(root)))

setup(name="not-so-badass",
      version=version,
      description="(not so) bad assessments",
      long_description=long_description,
      long_description_content_type="text/markdown",
      url="https://github.com/fpom/badass",
      author="Franck Pommereau",
      author_email="franck.pommereau@univ-evry.fr",
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Education",
                   "Topic :: Education",
                   "License :: OSI Approved :: GNU General Public License (GPL)",
                   "Programming Language :: Python :: 3.7",
                   "Operating System :: OS Independent"],
      packages=find_packages(where="."),
      python_requires=">=3.9",
      install_requires=["flask",
                        "flask_login",
                        "PyYAML",
                        "Headers-as-Dependencies",
                        "numpy",
                        "pandas",
                        "openpyxl",
                        "markdown",
                        "pexpect",
                        "jsonpath-ng",
                        "Pygments",
                        "tree_sitter",
                        "sympy",
                        "tqdm",
                        "pydal",
                        "seaborn",
                        "colorama",
                        "ipdb",
                        "parsedatetime",
                        "chardet",
                        "tree-sitter",
                        "matplotlib"],
      package_data={"badass" : data},
      entry_points={"console_scripts": ["badass=badass.__main__:main"]})
