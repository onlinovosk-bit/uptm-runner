"""UPTM-009: proof that the syntax gate reads what it claims to read.

Criteria are preregistered in ``docs/specs/UPTM-009-ci-syntax-gate.md``, written
before this file existed. Each test names the criterion it discharges.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from runner.syntax_gate import ROOT, Problem, main, run

# ``a32a5ee``'s workflow, quoted exactly from the commit: a deleted step kept
# beside the step that replaced it. The first exited 2 on an argument that no
# longer existed, so the second never ran.
A32A5EE_WORKFLOW = """\
name: Pytest
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Run pytest
        run: python -m pytest
      - name: Enforcement evidence (UPTM-006)
        run: python -m runner.cli enforcement-evidence --commit "${{ github.sha }}"
      - name: Enforcement evidence (UPTM-006, Evidence Rule A)
        run: python -m runner.cli enforcement-evidence
"""

# ``6b46cc2``'s shape: a merge left a tuple open. Reproduced rather than quoted
# - the commit's file is 900 lines and CI checks out one commit deep, so a test
# that reached for the history would pass here and fail in CI.
UNTERMINATED_TUPLE = """\
ROUTES = (
    Route("P12-R1"),
    Route("P12-R2"),

def next_thing():
    return None
"""


def _tree(root: Path, files: dict[str, str]) -> Path:
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    return root


def _kinds(problems: list[Problem]) -> list[tuple[str, str]]:
    return [(p.path, p.kind) for p in problems]


def test_g7_a_clean_tree_is_silent_and_exits_zero(tmp_path, capsys):
    _tree(
        tmp_path,
        {
            "mod.py": "x = 1\n",
            "data.json": '{"a": 1}\n',
            ".github/workflows/ci.yml": "name: CI\non: [push]\njobs: {}\n",
        },
    )
    assert run(tmp_path) == []
    assert main([str(tmp_path)]) == 0


def test_g1_a_python_file_that_does_not_parse_is_named_with_its_line(tmp_path):
    _tree(tmp_path, {"pkg/broken.py": UNTERMINATED_TUPLE, "pkg/fine.py": "y = 2\n"})
    problems = run(tmp_path)
    assert len(problems) == 1
    problem = problems[0]
    assert problem.path == "pkg/broken.py"
    assert problem.kind == "python"
    assert problem.line is not None
    # The interpreter's own message, not a paraphrase: a gate that rewrites the
    # diagnostic makes the reader guess what the parser actually said.
    with pytest.raises(SyntaxError) as raised:
        ast.parse(UNTERMINATED_TUPLE)
    assert problem.message == raised.value.msg


def test_r1_the_shape_that_swallowed_482_tests_is_reported(tmp_path):
    """R1: ``6b46cc2`` reached CI as a collection error naming the collector."""
    _tree(tmp_path, {"runner/enforcement.py": UNTERMINATED_TUPLE})
    problems = run(tmp_path)
    assert [p.path for p in problems] == ["runner/enforcement.py"]
    assert "never closed" in problems[0].message
    assert main([str(tmp_path)]) == 1


def test_g2_a_json_file_that_does_not_parse_is_named_with_its_line(tmp_path):
    # The shape found on main by this gate's first run: a merge concatenated two
    # required lists and dropped the comma between them.
    broken = '{\n  "required": [\n    "stale_on"\n    "wave_context"\n  ]\n}\n'
    _tree(tmp_path, {"schemas/evidence.schema.json": broken})
    problems = run(tmp_path)
    assert _kinds(problems) == [("schemas/evidence.schema.json", "json")]
    assert problems[0].line == 4
    with pytest.raises(json.JSONDecodeError) as raised:
        json.loads(broken)
    assert problems[0].message == raised.value.msg


def test_g3_a_workflow_that_is_not_yaml_is_reported(tmp_path):
    _tree(tmp_path, {".github/workflows/ci.yml": "name: CI\n  bad: [unclosed\n"})
    problems = run(tmp_path)
    assert _kinds(problems) == [(".github/workflows/ci.yml", "workflow")]


def test_r2_two_steps_running_one_subcommand_are_reported_with_both_names(tmp_path):
    """R2: ``a32a5ee``'s shape, quoted from the commit."""
    _tree(tmp_path, {".github/workflows/pytest.yml": A32A5EE_WORKFLOW})
    problems = run(tmp_path)
    assert len(problems) == 1
    message = problems[0].message
    assert "enforcement-evidence" in message
    assert "Enforcement evidence (UPTM-006)" in message
    assert "Enforcement evidence (UPTM-006, Evidence Rule A)" in message
    # 'pytest' is not a runner.cli subcommand and must not be counted.
    assert "pytest" not in message
    assert main([str(tmp_path)]) == 1


def test_g4_the_same_subcommand_in_two_different_jobs_is_not_a_finding(tmp_path):
    """The rule is about one job's step list, not about the workflow at large."""
    workflow = """\
name: CI
on: [push]
jobs:
  first:
    steps:
      - name: Evidence
        run: python -m runner.cli enforcement-evidence
  second:
    steps:
      - name: Evidence again
        run: python -m runner.cli enforcement-evidence
"""
    _tree(tmp_path, {".github/workflows/ci.yml": workflow})
    assert run(tmp_path) == []


def test_g4_the_console_script_spelling_counts_as_the_same_subcommand(tmp_path):
    """``uptm-runner x`` and ``python -m runner.cli x`` are one subcommand."""
    workflow = """\
name: CI
on: [push]
jobs:
  test:
    steps:
      - name: Module form
        run: python -m runner.cli mutation-gate
      - name: Console script form
        run: uptm-runner mutation-gate
"""
    _tree(tmp_path, {".github/workflows/ci.yml": workflow})
    problems = run(tmp_path)
    assert len(problems) == 1
    assert "mutation-gate" in problems[0].message


def test_g5_every_problem_is_reported_not_only_the_first(tmp_path):
    _tree(
        tmp_path,
        {
            "a.py": UNTERMINATED_TUPLE,
            "b.py": "def f(:\n",
            "c.json": "{,}",
            ".github/workflows/ci.yml": A32A5EE_WORKFLOW,
        },
    )
    problems = run(tmp_path)
    assert sorted(_kinds(problems)) == [
        (".github/workflows/ci.yml", "workflow"),
        ("a.py", "python"),
        ("b.py", "python"),
        ("c.json", "json"),
    ]


def test_g8_generated_trees_are_excluded_by_directory_name_at_any_depth(tmp_path):
    _tree(
        tmp_path,
        {
            "pkg/__pycache__/stale.py": UNTERMINATED_TUPLE,
            "deep/nest/node_modules/pkg/broken.json": "{,}",
            "kept.py": "ok = 1\n",
        },
    )
    assert run(tmp_path) == []


def test_g6_the_gate_imports_nothing_from_the_tree_it_validates():
    """Derived from the module's own AST, not asserted from memory.

    Were the gate to import ``runner.enforcement``, ``6b46cc2`` would have
    reached it as an ImportError traceback before the first file was read -
    which is the failure it exists to replace.
    """
    source = (ROOT / "runner" / "syntax_gate.py").read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module.split(".")[0])
    assert "runner" not in imported
    assert imported <= {"ast", "json", "re", "sys", "dataclasses", "pathlib",
                        "typing", "__future__", "yaml"}


def test_l2_this_repository_passes_its_own_gate():
    """The criteria are asserted against the real tree, not only fixtures."""
    assert run(ROOT) == []
