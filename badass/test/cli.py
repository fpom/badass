import argparse, sys

from colorama import Style as S, Fore as F
from pathlib import Path

from . import badass_run, badparse, report

def die (msg, code=1) :
    sys.stderr.write(f"{F.RED}{S.BRIGHT}error:{S.RESET_ALL} {msg.strip()}\n")
    sys.exit(code)

def file_exists (path) :
    if not path.exists() :
        die(f"not found: {path}")
    return path

def add_arguments (sub) :
    sub.add_argument("-b", "--badass", type=str, default="badass", metavar="DIR",
                     help="where to find *.bad scripts")
    sub.add_argument("-t", "--test", type=str, default="test", metavar="DIR",
                     help="where to store tests")
    sub.add_argument("-s", "--source", default="src", metavar="DIR",
                     help="where to find source files")
    sub.add_argument("-c", "--csv", type=str, default="badass.csv", metavar="CSV",
                     help="path for 'badass.csv' file with exercises")
    sub.add_argument("-d", "--debug", default=False, action="store_true",
                     help="run badass in debug mode")
    sub.add_argument("exercise", type=str,
                     help="exercise to test")

def main (args) :
    exo_question = args.exercise.split(".", 1)
    if len(exo_question) == 1 :
        exo_question.append("0")
    badass_dir = Path(args.badass)
    source_dir = Path(args.source)
    for spec in badparse(args.csv) :
        if [spec["exo"], spec["question"]] == exo_question :
            badass_script = file_exists(badass_dir / spec["script"])
            sources = [file_exists(source_dir / src) for src in spec["source"]]
            test_dir = Path(args.test) / badass_script.stem
            badass_run(badass_script, sources, test_dir, spec.get("input", []), args.debug)
            break
    else :
        die(f"exercise {args.exercise} not found in {args.csv}")
    report(test_dir / "report.zip")
