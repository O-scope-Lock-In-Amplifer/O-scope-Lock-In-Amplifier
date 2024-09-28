"""
Package build tasks script.

Tasks are functions which can be run from the command line by running this file
and passing their name (as long as they're decorated with ``_collect_task``).
Tasks very intentionally do not have any way of getting additional arguments
from the command line - they must take a fixed course of action and provide no
further options. Tasks will return True on success, False on failure, which
results in exit codes of 0 and -1, respectively. "Failure" means that there's
something wrong in this repository that should be fixed.
"""
###############################################################################
# Project: Turn your oscilloscope into a lock in amplifier with this one simple trick!
# File: tasks.py
#
# Copyright (c) 2024 Marcus Engineering, LLC
#
# Date         Comment                                          Eng
# -----------------------------------------------------------------------------
# 2024-03-21   Created from old setup.py.                       jrowley
#
###############################################################################

import os
from pathlib import Path
import sys
from typing import Callable, TypeAlias

import pytest

_TTC: TypeAlias = Callable[[], bool]

_tasks: dict[str, _TTC] = {}


def _collect_task(fn: _TTC) -> _TTC:
	"""Decorate a function so it's available at the command line."""
	global _tasks
	_tasks[fn.__name__] = fn
	return fn


def _pyrun(cmd: str) -> int:
	"""Call the current Python interpreter."""
	if (sys.executable is None) or (len(sys.executable) < 1):
		raise RuntimeError("Unknown interpreter!")
	interpreter = sys.executable
	res = os.system(f'""{interpreter}" {cmd}"')
	if os.name == "posix":
		res = os.waitstatus_to_exitcode(res)
	return res


@_collect_task
def run_tests() -> bool:
	"""Discover and run all tests in the tests folder."""
	tests_dir = Path(__file__).parent.absolute() / "tests"
	if not tests_dir.exists() or not tests_dir.is_dir():
		print(f"Tests directory {tests_dir} not found.")
		return False
	res = pytest.main([str(tests_dir)])
	if res != 0:
		print("Unit tests failed!")
		return False
	else:
		print("All unit tests passed.")
		return True


@_collect_task
def check_formatting() -> bool:
	"""Run our standard suite of code quality tools."""
	basepath = Path(__file__).parent.absolute()

	cmds = {
		"Black": f'-m black --check "{basepath}"',
		"Flake8": f'-m flake8 "{basepath}"',
		"MyPy": f'-m mypy "{basepath}"',
	}

	res: dict[str, int] = {}

	for k, cmd in cmds.items():
		res[k] = _pyrun(cmd)

	for k, r in res.items():
		if r != 0:
			print(f"{k} returned non 0 exit code!\n\tRan {cmds[k]}\n\tGot: {r}")

	if any(r != 0 for r in res.values()):
		print("Code check failure!")
		return False
	else:
		return True


@_collect_task
def build_docs() -> bool:
	"""Build our documentation outputs."""
	source_dir = Path(__file__).parent.absolute() / "docs"
	os.chdir(source_dir)
	res = _pyrun("-m sphinx.cmd.build -M latexpdf . _build")
	if res != 0:
		print("Sphinx failed!")
		return False
	else:
		return True


@_collect_task
def blacken() -> bool:
	"""Automatically reformat everything with Black."""
	basepath = Path(__file__).parent.absolute()
	res = _pyrun(f'-m black "{basepath}"')
	if res != 0:
		print("Black failed!")
		return False
	else:
		return True


def main() -> None:
	"""Run a task."""
	global _tasks

	if len(sys.argv) < 2:
		print("Specify a task. Available options:")
		for task_name in _tasks:
			print(task_name)
		sys.exit(-1)
	task_sel = sys.argv[1].strip()
	if task_sel not in _tasks:
		print(f'"{task_sel}" is not a task. Available options:')
		for task_name in _tasks:
			print(task_name)
		sys.exit(-1)

	task = _tasks[task_sel]
	if task():
		sys.exit(0)
	else:
		sys.exit(-1)


if __name__ == "__main__":
	main()
else:
	raise RuntimeError("Don't import this file.")
