from setuptools import setup, find_packages
from os import path
import badass

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(name="not-so-badass",
      version=badass.VERSION,
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
      python_requires=">=3.7",
      install_requires=["lxml", "pandas", "colorama", "clang", "chardet"],
      package_data={},
      entry_points={"console_scripts": ["badass=badass.__main__:main"]})
